"""
Behavioral RTL Simulation Engine.

Extends the digital engine with support for:
- always @(posedge/negedge) sequential blocks
- always @(*) combinational blocks
- if/else, case statements
- Non-blocking (<=) and blocking (=) assignments
- Multi-bit arithmetic (+, -, *, comparisons)
- Functions and tasks
- Verilog-style number literals (8'hFF, 16'd100, etc.)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import re
import copy


# ── Multi-bit value representation ──

class BitVec:
    """Fixed-width bit vector with X/Z support."""
    __slots__ = ('width', '_val', '_xz')

    def __init__(self, width: int = 1, val: int = 0, xz: int = 0):
        self.width = width
        mask = (1 << width) - 1
        self._val = val & mask
        self._xz = xz & mask      # bits set = X or Z

    @staticmethod
    def from_int(val: int, width: int = 32) -> 'BitVec':
        return BitVec(width, val)

    @staticmethod
    def x(width: int = 1) -> 'BitVec':
        return BitVec(width, 0, (1 << width) - 1)

    @staticmethod
    def parse_literal(s: str) -> 'BitVec':
        """Parse Verilog number literal: 8'hFF, 4'b1010, 16'd255, plain int."""
        s = s.strip().replace('_', '')
        m = re.match(r"(\d+)'([bBoOdDhH])([0-9a-fA-FxXzZ]+)", s)
        if m:
            width = int(m.group(1))
            base_ch = m.group(2).lower()
            digits = m.group(3).lower()
            base = {'b': 2, 'o': 8, 'd': 10, 'h': 16}[base_ch]
            if 'x' in digits or 'z' in digits:
                return BitVec.x(width)
            return BitVec(width, int(digits, base))
        # Plain integer
        try:
            v = int(s, 0)
            return BitVec(32, v)
        except ValueError:
            return BitVec.x(32)

    def to_int(self) -> int:
        if self._xz:
            return 0
        return self._val

    def to_signed(self) -> int:
        v = self.to_int()
        if v >= (1 << (self.width - 1)):
            v -= (1 << self.width)
        return v

    @property
    def is_x(self) -> bool:
        return self._xz != 0

    def bit(self, idx: int) -> int:
        if self._xz & (1 << idx):
            return -1  # X
        return (self._val >> idx) & 1

    def slice(self, hi: int, lo: int) -> 'BitVec':
        w = hi - lo + 1
        mask = (1 << w) - 1
        return BitVec(w, (self._val >> lo) & mask, (self._xz >> lo) & mask)

    def concat(self, other: 'BitVec') -> 'BitVec':
        """self is MSB part, other is LSB part."""
        w = self.width + other.width
        v = (self._val << other.width) | other._val
        x = (self._xz << other.width) | other._xz
        return BitVec(w, v, x)

    def _mask(self) -> int:
        return (1 << self.width) - 1

    # Arithmetic
    def __add__(self, other: 'BitVec') -> 'BitVec':
        if self._xz or other._xz:
            return BitVec.x(max(self.width, other.width))
        w = max(self.width, other.width)
        return BitVec(w, self._val + other._val)

    def __sub__(self, other: 'BitVec') -> 'BitVec':
        if self._xz or other._xz:
            return BitVec.x(max(self.width, other.width))
        w = max(self.width, other.width)
        return BitVec(w, (self._val - other._val) & ((1 << w) - 1))

    def __mul__(self, other: 'BitVec') -> 'BitVec':
        if self._xz or other._xz:
            return BitVec.x(self.width + other.width)
        w = self.width + other.width
        return BitVec(w, self._val * other._val)

    def __and__(self, other: 'BitVec') -> 'BitVec':
        w = max(self.width, other.width)
        return BitVec(w, self._val & other._val, self._xz | other._xz)

    def __or__(self, other: 'BitVec') -> 'BitVec':
        w = max(self.width, other.width)
        return BitVec(w, self._val | other._val, self._xz | other._xz)

    def __xor__(self, other: 'BitVec') -> 'BitVec':
        w = max(self.width, other.width)
        return BitVec(w, self._val ^ other._val, self._xz | other._xz)

    def __invert__(self) -> 'BitVec':
        return BitVec(self.width, (~self._val) & self._mask(), self._xz)

    def __lshift__(self, n: int) -> 'BitVec':
        return BitVec(self.width, (self._val << n) & self._mask())

    def __rshift__(self, n: int) -> 'BitVec':
        return BitVec(self.width, self._val >> n)

    # Comparison — return 1-bit BitVec
    def eq(self, other: 'BitVec') -> 'BitVec':
        if self._xz or other._xz:
            return BitVec.x(1)
        return BitVec(1, int(self._val == other._val))

    def ne(self, other: 'BitVec') -> 'BitVec':
        if self._xz or other._xz:
            return BitVec.x(1)
        return BitVec(1, int(self._val != other._val))

    def lt(self, other: 'BitVec') -> 'BitVec':
        if self._xz or other._xz:
            return BitVec.x(1)
        return BitVec(1, int(self._val < other._val))

    def le(self, other: 'BitVec') -> 'BitVec':
        if self._xz or other._xz:
            return BitVec.x(1)
        return BitVec(1, int(self._val <= other._val))

    def gt(self, other: 'BitVec') -> 'BitVec':
        if self._xz or other._xz:
            return BitVec.x(1)
        return BitVec(1, int(self._val > other._val))

    def ge(self, other: 'BitVec') -> 'BitVec':
        if self._xz or other._xz:
            return BitVec.x(1)
        return BitVec(1, int(self._val >= other._val))

    def logical_and(self, other: 'BitVec') -> 'BitVec':
        return BitVec(1, int(bool(self._val) and bool(other._val)))

    def logical_or(self, other: 'BitVec') -> 'BitVec':
        return BitVec(1, int(bool(self._val) or bool(other._val)))

    def logical_not(self) -> 'BitVec':
        return BitVec(1, int(self._val == 0))

    def reduce_or(self) -> 'BitVec':
        return BitVec(1, int(self._val != 0))

    def reduce_and(self) -> 'BitVec':
        return BitVec(1, int(self._val == self._mask()))

    def __bool__(self) -> bool:
        return self._val != 0 and self._xz == 0

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BitVec):
            return self._val == other._val and self._xz == other._xz
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._val, self._xz, self.width))

    def __repr__(self) -> str:
        if self._xz:
            return f"{self.width}'x"
        return f"{self.width}'h{self._val:0{(self.width+3)//4}x}"


# ── AST nodes for parsed behavioral Verilog ──

@dataclass
class ASTNode:
    """Base AST node."""
    pass

@dataclass
class NumberLit(ASTNode):
    value: BitVec

@dataclass
class Identifier(ASTNode):
    name: str

@dataclass
class BitSelect(ASTNode):
    name: str
    index: ASTNode

@dataclass
class PartSelect(ASTNode):
    name: str
    hi: ASTNode
    lo: ASTNode

@dataclass
class UnaryOp(ASTNode):
    op: str
    operand: ASTNode

@dataclass
class BinaryOp(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode

@dataclass
class TernaryOp(ASTNode):
    cond: ASTNode
    true_expr: ASTNode
    false_expr: ASTNode

@dataclass
class Concat(ASTNode):
    parts: List[ASTNode]

@dataclass
class FuncCall(ASTNode):
    name: str
    args: List[ASTNode]

@dataclass
class BlockingAssign(ASTNode):
    lhs: ASTNode
    rhs: ASTNode

@dataclass
class NonBlockingAssign(ASTNode):
    lhs: ASTNode
    rhs: ASTNode

@dataclass
class IfElse(ASTNode):
    cond: ASTNode
    then_body: List[ASTNode]
    else_body: List[ASTNode]

@dataclass
class CaseStmt(ASTNode):
    expr: ASTNode
    items: List[Tuple[List[ASTNode], List[ASTNode]]]  # [(values, stmts)]
    default: List[ASTNode]

@dataclass
class ForLoop(ASTNode):
    init: ASTNode
    cond: ASTNode
    incr: ASTNode
    body: List[ASTNode]

@dataclass
class AlwaysBlock(ASTNode):
    sensitivity: List[Tuple[str, str]]  # [(edge_type, signal_name)]
    body: List[ASTNode]
    is_combinational: bool = False

@dataclass
class ContinuousAssign(ASTNode):
    lhs: ASTNode
    rhs: ASTNode

@dataclass
class ModuleDef(ASTNode):
    name: str
    ports: List[str]
    port_dirs: Dict[str, str]       # name -> "input"/"output"/"inout"
    port_widths: Dict[str, int]     # name -> width
    signals: Dict[str, Tuple[int, bool]]  # name -> (width, is_reg)
    always_blocks: List[AlwaysBlock]
    assigns: List[ContinuousAssign]
    functions: Dict[str, Any]
    localparams: Dict[str, BitVec]


# ── RTL Parser ──

class RTLParser:
    """Parse behavioral Verilog into AST."""

    def __init__(self, code: str):
        self._raw = code
        self._tokens: List[str] = []
        self._pos = 0
        self._tokenize(code)

    # ── Tokenizer ──

    def _tokenize(self, code: str):
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

        pat = re.compile(
            r"""(\d+'[bBoOdDhH][0-9a-fA-FxXzZ_]+)"""   # verilog literals
            r"""|(\d+\.\d+)"""                            # float (unused but safe)
            r"""|(\d+)"""                                 # decimal
            r"""|(<=|>=|==|!=|===|!==|&&|\|\||<<|>>|->)"""  # multi-char ops
            r"""|([a-zA-Z_]\w*)"""                        # identifiers
            r"""|([ \t\r\n]+)"""                           # whitespace (skip)
            r"""|(.)""",                                  # single char
            re.DOTALL
        )
        self._tokens = []
        for m in pat.finditer(code):
            tok = m.group(0)
            if tok.strip():
                self._tokens.append(tok)
        self._pos = 0

    def _cur(self) -> Optional[str]:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _peek(self, offset: int = 0) -> Optional[str]:
        idx = self._pos + offset
        return self._tokens[idx] if idx < len(self._tokens) else None

    def _adv(self) -> str:
        t = self._tokens[self._pos]
        self._pos += 1
        return t

    def _expect(self, tok: str):
        got = self._adv()
        if got != tok:
            raise SyntaxError(f"Expected '{tok}', got '{got}' at token {self._pos}")

    def _match(self, tok: str) -> bool:
        if self._cur() == tok:
            self._adv()
            return True
        return False

    def _skip_to(self, tok: str):
        while self._cur() is not None and self._cur() != tok:
            self._adv()

    # ── Top-level ──

    def parse_module(self) -> ModuleDef:
        self._expect('module')
        name = self._adv()

        # Port list
        self._expect('(')

        mod = ModuleDef(
            name=name, ports=[],
            port_dirs={}, port_widths={},
            signals={}, always_blocks=[], assigns=[],
            functions={}, localparams={}
        )

        self._parse_port_list(mod)
        self._expect(')')
        self._expect(';')

        while self._cur() not in (None, 'endmodule'):
            self._parse_module_item(mod)

        if self._cur() == 'endmodule':
            self._adv()
        return mod

    def _parse_port_list(self, mod: ModuleDef):
        """Parse port list, handling ANSI-style inline declarations."""
        while self._cur() != ')':
            direction = None
            is_reg = False
            width = 1

            # Check for direction keyword
            if self._cur() in ('input', 'output', 'inout'):
                direction = self._adv()
                if self._cur() in ('wire', 'reg'):
                    is_reg = (self._cur() == 'reg')
                    self._adv()
                # Width
                if self._cur() == '[':
                    self._adv()
                    msb = self._parse_const_expr()
                    self._expect(':')
                    lsb = self._parse_const_expr()
                    self._expect(']')
                    width = msb - lsb + 1

            tok = self._cur()
            if tok and tok not in (',', ')'):
                name = self._adv()
                mod.ports.append(name)
                if direction:
                    mod.port_dirs[name] = direction
                    mod.port_widths[name] = width
                    mod.signals[name] = (width, is_reg or direction == 'output')
            if self._cur() == ',':
                self._adv()

    def _parse_module_item(self, mod: ModuleDef):
        kw = self._cur()

        if kw in ('input', 'output', 'inout'):
            self._parse_io_decl(mod)
        elif kw == 'wire':
            self._parse_signal_decl(mod, False)
        elif kw == 'reg':
            self._parse_signal_decl(mod, True)
        elif kw == 'localparam' or kw == 'parameter':
            self._parse_localparam(mod)
        elif kw == 'assign':
            self._parse_cont_assign(mod)
        elif kw == 'always':
            self._parse_always(mod)
        elif kw == 'function':
            self._parse_function(mod)
        elif kw == 'task':
            self._skip_block('task', 'endtask')
        elif kw == 'initial':
            self._skip_block_begin()
        elif kw in ('and', 'or', 'not', 'nand', 'nor', 'xor', 'xnor', 'buf'):
            self._skip_to(';')
            self._adv()
        else:
            self._adv()

    # ── Declarations ──

    def _parse_width(self) -> int:
        if self._cur() == '[':
            self._adv()
            msb = self._parse_const_expr()
            self._expect(':')
            lsb = self._parse_const_expr()
            self._expect(']')
            return msb - lsb + 1
        return 1

    def _parse_const_expr(self) -> int:
        """Parse constant expression (for widths, localparams)."""
        return self._eval_const(self._parse_expr())

    def _eval_const(self, node: ASTNode) -> int:
        if isinstance(node, NumberLit):
            return node.value.to_int()
        if isinstance(node, BinaryOp):
            l = self._eval_const(node.left)
            r = self._eval_const(node.right)
            ops = {'+': lambda a, b: a+b, '-': lambda a, b: a-b,
                   '*': lambda a, b: a*b, '/': lambda a, b: a//b if b else 0}
            return ops.get(node.op, lambda a, b: 0)(l, r)
        return 0

    def _parse_io_decl(self, mod: ModuleDef):
        direction = self._adv()  # input/output/inout
        if self._cur() in ('wire', 'reg'):
            self._adv()
        width = self._parse_width()
        while True:
            name = self._adv()
            mod.port_dirs[name] = direction
            mod.port_widths[name] = width
            mod.signals[name] = (width, direction == 'output')
            if self._cur() == ',':
                self._adv()
            else:
                break
        self._expect(';')

    def _parse_signal_decl(self, mod: ModuleDef, is_reg: bool):
        self._adv()  # wire/reg
        width = self._parse_width()
        while True:
            name = self._adv()
            # Array declaration: reg [7:0] data_buf [0:7];
            if self._cur() == '[':
                self._adv()
                lo = self._parse_const_expr()
                self._expect(':')
                hi = self._parse_const_expr()
                self._expect(']')
                # Store as array — we'll flatten in the engine
                for i in range(lo, hi + 1):
                    arr_name = f"{name}_{i}"
                    mod.signals[arr_name] = (width, is_reg)
                mod.signals[name] = (width, is_reg)  # base entry
                mod.signals[f"{name}__array"] = (hi - lo + 1, True)
            else:
                mod.signals[name] = (width, is_reg)
            if self._cur() == ',':
                self._adv()
            else:
                break
        self._expect(';')

    def _parse_localparam(self, mod: ModuleDef):
        self._adv()  # localparam/parameter
        # Optional width
        if self._cur() == '[':
            self._parse_width()
        # Can have multiple paramters or a single one
        # localparam [3:0] ST_IDLE = 4'd0, ST_BREAK = 4'd1;
        while True:
            name = self._adv()
            self._expect('=')
            expr = self._parse_expr()
            val = self._eval_const(expr)
            mod.localparams[name] = BitVec.from_int(val)
            if self._cur() == ',':
                self._adv()
            else:
                break
        self._expect(';')

    def _parse_cont_assign(self, mod: ModuleDef):
        self._adv()  # assign
        lhs = self._parse_lvalue()
        self._expect('=')
        rhs = self._parse_expr()
        self._expect(';')
        mod.assigns.append(ContinuousAssign(lhs, rhs))

    # ── Always blocks ──

    def _parse_always(self, mod: ModuleDef):
        self._adv()  # always
        sens = self._parse_sensitivity()
        body = self._parse_block_or_stmt()
        is_comb = len(sens) == 0 or (len(sens) == 1 and sens[0][0] == '*')
        blk = AlwaysBlock(sensitivity=sens, body=body, is_combinational=is_comb)
        mod.always_blocks.append(blk)

    def _parse_sensitivity(self) -> List[Tuple[str, str]]:
        sens: List[Tuple[str, str]] = []
        if self._cur() != '@':
            return sens
        self._adv()  # @
        if self._cur() == '(':
            self._adv()
            if self._cur() == '*':
                sens.append(('*', '*'))
                self._adv()
            else:
                while self._cur() != ')':
                    edge = 'level'
                    if self._cur() in ('posedge', 'negedge'):
                        edge = self._adv()
                    sig = self._adv()
                    sens.append((edge, sig))
                    if self._cur() == 'or' or self._cur() == ',':
                        self._adv()
            self._expect(')')
        return sens

    def _parse_block_or_stmt(self) -> List[ASTNode]:
        if self._cur() == 'begin':
            return self._parse_begin_end()
        return [self._parse_stmt()]

    def _parse_begin_end(self) -> List[ASTNode]:
        self._expect('begin')
        # Optional block label
        if self._cur() == ':':
            self._adv()
            self._adv()  # label name
        stmts: List[ASTNode] = []
        while self._cur() != 'end':
            stmts.append(self._parse_stmt())
        self._expect('end')
        return stmts

    def _parse_stmt(self) -> ASTNode:
        kw = self._cur()
        if kw == 'if':
            return self._parse_if()
        elif kw == 'case' or kw == 'casex' or kw == 'casez':
            return self._parse_case()
        elif kw == 'for':
            return self._parse_for()
        elif kw == 'begin':
            stmts = self._parse_begin_end()
            # Wrap in if(1) to keep as statement list — or just return first
            if len(stmts) == 1:
                return stmts[0]
            return IfElse(NumberLit(BitVec(1, 1)), stmts, [])
        else:
            return self._parse_assignment_stmt()

    def _parse_if(self) -> IfElse:
        self._expect('if')
        self._expect('(')
        cond = self._parse_expr()
        self._expect(')')
        then_body = self._parse_block_or_stmt()
        else_body: List[ASTNode] = []
        if self._cur() == 'else':
            self._adv()
            else_body = self._parse_block_or_stmt()
        return IfElse(cond, then_body, else_body)

    def _parse_case(self) -> CaseStmt:
        self._adv()  # case/casex/casez
        self._expect('(')
        expr = self._parse_expr()
        self._expect(')')

        items: List[Tuple[List[ASTNode], List[ASTNode]]] = []
        default: List[ASTNode] = []

        while self._cur() not in (None, 'endcase'):
            if self._cur() == 'default':
                self._adv()
                self._expect(':')
                default = self._parse_block_or_stmt()
            else:
                # Case values (possibly comma-separated)
                vals: List[ASTNode] = []
                while True:
                    vals.append(self._parse_expr())
                    if self._cur() == ',':
                        self._adv()
                    else:
                        break
                self._expect(':')
                body = self._parse_block_or_stmt()
                items.append((vals, body))

        self._expect('endcase')
        return CaseStmt(expr, items, default)

    def _parse_for(self) -> ForLoop:
        self._expect('for')
        self._expect('(')
        init = self._parse_assignment_stmt_no_semi()
        self._expect(';')
        cond = self._parse_expr()
        self._expect(';')
        incr = self._parse_assignment_stmt_no_semi()
        self._expect(')')
        body = self._parse_block_or_stmt()
        return ForLoop(init, cond, incr, body)

    def _parse_assignment_stmt(self) -> ASTNode:
        lhs = self._parse_lvalue()
        if self._cur() == '<=':
            self._adv()
            rhs = self._parse_expr()
            self._expect(';')
            return NonBlockingAssign(lhs, rhs)
        elif self._cur() == '=':
            self._adv()
            rhs = self._parse_expr()
            self._expect(';')
            return BlockingAssign(lhs, rhs)
        else:
            # Bare expression (task call etc) — skip to semicolon
            self._skip_to(';')
            self._adv()
            return BlockingAssign(lhs, NumberLit(BitVec(1, 0)))

    def _parse_assignment_stmt_no_semi(self) -> ASTNode:
        lhs = self._parse_lvalue()
        if self._cur() == '<=':
            self._adv()
            rhs = self._parse_expr()
            return NonBlockingAssign(lhs, rhs)
        elif self._cur() == '=':
            self._adv()
            rhs = self._parse_expr()
            return BlockingAssign(lhs, rhs)
        return BlockingAssign(lhs, NumberLit(BitVec(1, 0)))

    def _parse_lvalue(self) -> ASTNode:
        name = self._adv()
        if self._cur() == '[':
            self._adv()
            idx = self._parse_expr()
            if self._cur() == ':':
                self._adv()
                lo = self._parse_expr()
                self._expect(']')
                return PartSelect(name, idx, lo)
            self._expect(']')
            return BitSelect(name, idx)
        return Identifier(name)

    # ── Expression parser (precedence climbing) ──

    def _parse_expr(self) -> ASTNode:
        return self._parse_ternary()

    def _parse_ternary(self) -> ASTNode:
        node = self._parse_logor()
        if self._cur() == '?':
            self._adv()
            t = self._parse_expr()
            self._expect(':')
            f = self._parse_expr()
            return TernaryOp(node, t, f)
        return node

    def _parse_logor(self) -> ASTNode:
        node = self._parse_logand()
        while self._cur() == '||':
            self._adv()
            node = BinaryOp('||', node, self._parse_logand())
        return node

    def _parse_logand(self) -> ASTNode:
        node = self._parse_bitor()
        while self._cur() == '&&':
            self._adv()
            node = BinaryOp('&&', node, self._parse_bitor())
        return node

    def _parse_bitor(self) -> ASTNode:
        node = self._parse_bitxor()
        while self._cur() == '|':
            self._adv()
            node = BinaryOp('|', node, self._parse_bitxor())
        return node

    def _parse_bitxor(self) -> ASTNode:
        node = self._parse_bitand()
        while self._cur() == '^':
            self._adv()
            node = BinaryOp('^', node, self._parse_bitand())
        return node

    def _parse_bitand(self) -> ASTNode:
        node = self._parse_equality()
        while self._cur() == '&':
            self._adv()
            node = BinaryOp('&', node, self._parse_equality())
        return node

    def _parse_equality(self) -> ASTNode:
        node = self._parse_comparison()
        while self._cur() in ('==', '!=', '===', '!=='):
            op = self._adv()
            node = BinaryOp(op, node, self._parse_comparison())
        return node

    def _parse_comparison(self) -> ASTNode:
        node = self._parse_shift()
        while self._cur() in ('<', '>', '<=', '>='):
            # Disambiguate <= (comparison vs non-blocking assign)
            # In expression context, it's always comparison
            op = self._adv()
            node = BinaryOp(op, node, self._parse_shift())
        return node

    def _parse_shift(self) -> ASTNode:
        node = self._parse_add()
        while self._cur() in ('<<', '>>'):
            op = self._adv()
            node = BinaryOp(op, node, self._parse_add())
        return node

    def _parse_add(self) -> ASTNode:
        node = self._parse_mul()
        while self._cur() in ('+', '-'):
            op = self._adv()
            node = BinaryOp(op, node, self._parse_mul())
        return node

    def _parse_mul(self) -> ASTNode:
        node = self._parse_unary()
        while self._cur() in ('*', '/', '%'):
            op = self._adv()
            node = BinaryOp(op, node, self._parse_unary())
        return node

    def _parse_unary(self) -> ASTNode:
        if self._cur() == '~':
            self._adv()
            return UnaryOp('~', self._parse_unary())
        if self._cur() == '!':
            self._adv()
            return UnaryOp('!', self._parse_unary())
        if self._cur() == '-' and self._peek(1) and self._peek(1)[0].isdigit():
            self._adv()
            inner = self._parse_primary()
            if isinstance(inner, NumberLit):
                v = inner.value.to_int()
                w = inner.value.width
                return NumberLit(BitVec(w, (-v) & ((1 << w) - 1)))
            return UnaryOp('-', inner)
        if self._cur() == '|':
            self._adv()
            return UnaryOp('|', self._parse_unary())  # reduction OR
        if self._cur() == '&':
            self._adv()
            return UnaryOp('&', self._parse_unary())  # reduction AND
        if self._cur() == '^':
            self._adv()
            return UnaryOp('^', self._parse_unary())  # reduction XOR
        return self._parse_primary()

    def _parse_primary(self) -> ASTNode:
        tok = self._cur()
        if tok is None:
            return NumberLit(BitVec.x(1))

        # Parenthesized expr
        if tok == '(':
            self._adv()
            node = self._parse_expr()
            self._expect(')')
            return node

        # Concatenation {a, b, c}
        if tok == '{':
            self._adv()
            parts: List[ASTNode] = []
            while self._cur() != '}':
                parts.append(self._parse_expr())
                if self._cur() == ',':
                    self._adv()
            self._expect('}')
            return Concat(parts)

        # Number literals
        if re.match(r"\d+'[bBoOdDhH]", tok):
            return NumberLit(BitVec.parse_literal(self._adv()))

        if tok.isdigit():
            return NumberLit(BitVec.from_int(int(self._adv())))

        # Identifier (possibly with bit/part select)
        if re.match(r'[a-zA-Z_]', tok):
            name = self._adv()
            if self._cur() == '[':
                self._adv()
                idx = self._parse_expr()
                if self._cur() == ':':
                    self._adv()
                    lo = self._parse_expr()
                    self._expect(']')
                    return PartSelect(name, idx, lo)
                self._expect(']')
                return BitSelect(name, idx)
            if self._cur() == '(':
                # Function call
                self._adv()
                args: List[ASTNode] = []
                while self._cur() != ')':
                    args.append(self._parse_expr())
                    if self._cur() == ',':
                        self._adv()
                self._expect(')')
                return FuncCall(name, args)
            return Identifier(name)

        # Fallback
        self._adv()
        return NumberLit(BitVec.x(1))

    # ── Helpers ──

    def _parse_function(self, mod: ModuleDef):
        """Parse function declaration — store body for later evaluation."""
        self._adv()  # function
        # Optional return width
        ret_width = self._parse_width()
        name = self._adv()
        self._expect(';')

        params: List[Tuple[str, int]] = []
        body: List[ASTNode] = []

        while self._cur() not in (None, 'endfunction'):
            if self._cur() == 'input':
                self._adv()
                w = self._parse_width()
                pname = self._adv()
                params.append((pname, w))
                self._expect(';')
            elif self._cur() == 'begin':
                body = self._parse_begin_end()
            else:
                body.append(self._parse_stmt())

        if self._cur() == 'endfunction':
            self._adv()

        mod.functions[name] = {
            'name': name, 'ret_width': ret_width,
            'params': params, 'body': body
        }

    def _skip_block(self, start: str, end: str):
        self._adv()  # start keyword
        depth = 1
        while self._cur() is not None and depth > 0:
            if self._cur() == start:
                depth += 1
            elif self._cur() == end:
                depth -= 1
            self._adv()

    def _skip_block_begin(self):
        self._adv()  # initial
        if self._cur() == 'begin':
            self._adv()
            depth = 1
            while self._cur() is not None and depth > 0:
                if self._cur() == 'begin':
                    depth += 1
                elif self._cur() == 'end':
                    depth -= 1
                self._adv()
        else:
            self._skip_to(';')
            self._adv()


# ── RTL Simulation Engine ──

class RTLSimulator:
    """
    Cycle-accurate behavioral Verilog simulator.

    Supports clocked always blocks, combinational logic,
    multi-bit arithmetic, if/else/case, for loops, functions.
    """

    def __init__(self):
        self._modules: Dict[str, ModuleDef] = {}
        self._regs: Dict[str, BitVec] = {}         # current register values
        self._next_regs: Dict[str, BitVec] = {}     # NBA target values
        self._widths: Dict[str, int] = {}
        self._localparams: Dict[str, BitVec] = {}
        self._functions: Dict[str, dict] = {}
        self._always_blocks: List[AlwaysBlock] = []
        self._assigns: List[ContinuousAssign] = []
        self._clk_sig: str = 'clk'
        self._rst_sig: str = 'rst_n'
        self._time: int = 0
        self._waveforms: Dict[str, List[Tuple[int, int]]] = {}
        self._arrays: Dict[str, Dict[int, BitVec]] = {}  # name -> {idx -> val}
        self._array_widths: Dict[str, int] = {}

    def load_verilog(self, code: str):
        """Parse and load a Verilog module."""
        parser = RTLParser(code)
        mod = parser.parse_module()
        self._modules[mod.name] = mod

        # Register signals
        for name, (width, is_reg) in mod.signals.items():
            if name.endswith('__array'):
                base = name.replace('__array', '')
                self._arrays[base] = {}
                self._array_widths[base] = width
                continue
            self._widths[name] = width
            self._regs[name] = BitVec.x(width)
            self._waveforms[name] = []

        # Localparams
        self._localparams.update(mod.localparams)

        # Functions
        self._functions.update(mod.functions)

        # Store blocks
        self._always_blocks = mod.always_blocks
        self._assigns = mod.assigns

    def set_input(self, name: str, value: int):
        """Set an input signal value."""
        w = self._widths.get(name, 1)
        self._regs[name] = BitVec.from_int(value, w)

    def get_output(self, name: str) -> int:
        """Get an output signal's integer value."""
        return self._regs.get(name, BitVec(1, 0)).to_int()

    def get_bitvec(self, name: str) -> BitVec:
        return self._regs.get(name, BitVec(1, 0))

    def _record(self):
        for name, bv in self._regs.items():
            if name in self._waveforms:
                self._waveforms[name].append((self._time, bv.to_int()))

    # ── Evaluation ──

    def _eval(self, node: ASTNode) -> BitVec:
        if isinstance(node, NumberLit):
            return node.value

        if isinstance(node, Identifier):
            name = node.name
            if name in self._regs:
                return self._regs[name]
            if name in self._localparams:
                return self._localparams[name]
            return BitVec.x(self._widths.get(name, 32))

        if isinstance(node, BitSelect):
            base = self._resolve_name(node.name)
            idx = self._eval(node.index).to_int()
            # Array access?
            if node.name in self._arrays:
                arr_name = f"{node.name}_{idx}"
                if arr_name in self._regs:
                    return self._regs[arr_name]
                return self._arrays[node.name].get(idx, BitVec.x(self._widths.get(arr_name, 8)))
            # Bit select on vector
            return base.slice(idx, idx)

        if isinstance(node, PartSelect):
            base = self._resolve_name(node.name)
            hi = self._eval(node.hi).to_int()
            lo = self._eval(node.lo).to_int()
            return base.slice(hi, lo)

        if isinstance(node, UnaryOp):
            v = self._eval(node.operand)
            if node.op == '~':
                return ~v
            if node.op == '!':
                return v.logical_not()
            if node.op == '-':
                return BitVec(v.width, (-v.to_int()) & ((1 << v.width) - 1))
            if node.op == '|':
                return v.reduce_or()
            if node.op == '&':
                return v.reduce_and()
            return v

        if isinstance(node, BinaryOp):
            l = self._eval(node.left)
            r = self._eval(node.right)
            op = node.op
            if op == '+':  return l + r
            if op == '-':  return l - r
            if op == '*':  return l * r
            if op == '&':  return l & r
            if op == '|':  return l | r
            if op == '^':  return l ^ r
            if op == '&&': return l.logical_and(r)
            if op == '||': return l.logical_or(r)
            if op == '==': return l.eq(r)
            if op == '!=': return l.ne(r)
            if op == '<':  return l.lt(r)
            if op == '>':  return l.gt(r)
            if op == '<=': return l.le(r)
            if op == '>=': return l.ge(r)
            if op == '<<': return l << r.to_int()
            if op == '>>': return l >> r.to_int()
            if op == '/':
                rv = r.to_int()
                return BitVec(l.width, l.to_int() // rv if rv else 0)
            if op == '%':
                rv = r.to_int()
                return BitVec(l.width, l.to_int() % rv if rv else 0)
            return BitVec.x(max(l.width, r.width))

        if isinstance(node, TernaryOp):
            c = self._eval(node.cond)
            if c.is_x:
                return BitVec.x(max(
                    self._eval(node.true_expr).width,
                    self._eval(node.false_expr).width))
            if bool(c):
                return self._eval(node.true_expr)
            return self._eval(node.false_expr)

        if isinstance(node, Concat):
            result = BitVec(0, 0)
            for part in node.parts:
                v = self._eval(part)
                result = result.concat(v)
            return result

        if isinstance(node, FuncCall):
            return self._eval_function(node.name, node.args)

        return BitVec.x(1)

    def _resolve_name(self, name: str) -> BitVec:
        if name in self._regs:
            return self._regs[name]
        if name in self._localparams:
            return self._localparams[name]
        return BitVec.x(self._widths.get(name, 1))

    def _eval_function(self, name: str, args: List[ASTNode]) -> BitVec:
        func = self._functions.get(name)
        if not func:
            return BitVec.x(1)

        # Set up local scope
        saved = {}
        for i, (pname, pw) in enumerate(func['params']):
            saved[pname] = self._regs.get(pname)
            if i < len(args):
                self._regs[pname] = self._eval(args[i])
                self._widths[pname] = pw
            else:
                self._regs[pname] = BitVec.x(pw)

        # Function return via assignment to function name
        ret_w = func['ret_width']
        saved[name] = self._regs.get(name)
        self._regs[name] = BitVec(ret_w, 0)
        self._widths[name] = ret_w

        for stmt in func['body']:
            self._exec(stmt)

        result = self._regs.get(name, BitVec(ret_w, 0))

        # Restore scope
        for k, v in saved.items():
            if v is None:
                self._regs.pop(k, None)
            else:
                self._regs[k] = v

        return result

    # ── Statement execution ──

    def _exec(self, node: ASTNode):
        if isinstance(node, BlockingAssign):
            val = self._eval(node.rhs)
            self._assign(node.lhs, val, blocking=True)

        elif isinstance(node, NonBlockingAssign):
            val = self._eval(node.rhs)
            self._assign(node.lhs, val, blocking=False)

        elif isinstance(node, IfElse):
            cond = self._eval(node.cond)
            if bool(cond):
                for s in node.then_body:
                    self._exec(s)
            else:
                for s in node.else_body:
                    self._exec(s)

        elif isinstance(node, CaseStmt):
            expr_val = self._eval(node.expr)
            matched = False
            for vals, stmts in node.items:
                for v in vals:
                    if self._eval(v).to_int() == expr_val.to_int():
                        matched = True
                        break
                if matched:
                    for s in stmts:
                        self._exec(s)
                    break
            if not matched:
                for s in node.default:
                    self._exec(s)

        elif isinstance(node, ForLoop):
            self._exec(node.init)
            max_iter = 10000
            for _ in range(max_iter):
                cond = self._eval(node.cond)
                if not bool(cond):
                    break
                for s in node.body:
                    self._exec(s)
                self._exec(node.incr)

    def _assign(self, lhs: ASTNode, val: BitVec, blocking: bool = True):
        if isinstance(lhs, Identifier):
            name = lhs.name
            w = self._widths.get(name, val.width)
            v = BitVec(w, val.to_int())
            if blocking:
                self._regs[name] = v
            else:
                self._next_regs[name] = v

        elif isinstance(lhs, BitSelect):
            name = lhs.name
            idx = self._eval(lhs.index).to_int()
            # Array element?
            if name in self._arrays:
                arr_name = f"{name}_{idx}"
                w = self._widths.get(arr_name, 8)
                v = BitVec(w, val.to_int())
                if blocking:
                    self._regs[arr_name] = v
                    self._arrays[name][idx] = v
                else:
                    self._next_regs[arr_name] = v
            else:
                # Bit assignment on vector
                cur = self._regs.get(name, BitVec.x(self._widths.get(name, 32)))
                new_val = cur.to_int()
                bit = val.to_int() & 1
                new_val = (new_val & ~(1 << idx)) | (bit << idx)
                w = self._widths.get(name, cur.width)
                result = BitVec(w, new_val)
                if blocking:
                    self._regs[name] = result
                else:
                    self._next_regs[name] = result

        elif isinstance(lhs, PartSelect):
            name = lhs.name
            hi = self._eval(lhs.hi).to_int()
            lo = self._eval(lhs.lo).to_int()
            cur = self._regs.get(name, BitVec.x(self._widths.get(name, 32)))
            cv = cur.to_int()
            w_slice = hi - lo + 1
            mask = ((1 << w_slice) - 1) << lo
            cv = (cv & ~mask) | ((val.to_int() & ((1 << w_slice) - 1)) << lo)
            w = self._widths.get(name, cur.width)
            result = BitVec(w, cv)
            if blocking:
                self._regs[name] = result
            else:
                self._next_regs[name] = result

    # ── Simulation control ──

    def reset(self, cycles: int = 2):
        """Apply reset for given number of cycles."""
        rst = self._rst_sig
        clk = self._clk_sig

        # Assert reset
        if rst in self._regs:
            if rst.endswith('_n') or rst.endswith('_b'):
                self._regs[rst] = BitVec(1, 0)  # active low
            else:
                self._regs[rst] = BitVec(1, 1)  # active high

        for _ in range(cycles):
            self._clock_edge(clk, rising=True)
            self._clock_edge(clk, rising=False)

        # De-assert reset
        if rst in self._regs:
            if rst.endswith('_n') or rst.endswith('_b'):
                self._regs[rst] = BitVec(1, 1)
            else:
                self._regs[rst] = BitVec(1, 0)

    def tick(self, n: int = 1):
        """Run n clock cycles."""
        for _ in range(n):
            self._clock_edge(self._clk_sig, rising=True)
            self._clock_edge(self._clk_sig, rising=False)

    def _clock_edge(self, clk: str, rising: bool = True):
        """Process one clock edge."""
        # Set clock
        self._regs[clk] = BitVec(1, 1 if rising else 0)
        self._time += 1

        # Evaluate combinational assigns
        self._eval_assigns()

        # Execute always blocks triggered by this edge
        self._next_regs.clear()

        for blk in self._always_blocks:
            if blk.is_combinational:
                for stmt in blk.body:
                    self._exec(stmt)
                continue

            triggered = False
            for edge, sig in blk.sensitivity:
                if edge == 'posedge' and sig == clk and rising:
                    triggered = True
                elif edge == 'negedge' and sig == clk and not rising:
                    triggered = True
                elif edge == 'posedge' and sig != clk:
                    # Check if this signal is 1 (for async reset)
                    v = self._regs.get(sig, BitVec(1, 0))
                    # posedge rst (active high) — trigger if value is high
                    if bool(v):
                        triggered = True
                elif edge == 'negedge' and sig != clk:
                    v = self._regs.get(sig, BitVec(1, 1))
                    # negedge rst_n (active low) — trigger if value is low
                    if not bool(v):
                        triggered = True

            if triggered:
                for stmt in blk.body:
                    self._exec(stmt)

        # Apply non-blocking assignments
        for name, val in self._next_regs.items():
            self._regs[name] = val
            if name in self._arrays:
                # Array NBA handled via arr_name already
                pass

        # Record waveforms
        self._record()

    def _eval_assigns(self):
        """Evaluate continuous assignments."""
        for asgn in self._assigns:
            val = self._eval(asgn.rhs)
            self._assign(asgn.lhs, val, blocking=True)

    def run(self, cycles: int, record_signals: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run simulation for specified cycles. Returns waveform data."""
        self._record()  # Initial state

        for _ in range(cycles):
            self.tick()

        # Build results
        results: Dict[str, Any] = {
            'type': 'rtl',
            'cycles': cycles,
            'time_scale': 1e-9,
        }

        sigs = record_signals or list(self._waveforms.keys())
        for name in sigs:
            if name in self._waveforms:
                wf = self._waveforms[name]
                results[name] = {
                    'times': [t for t, _ in wf],
                    'values': [v for _, v in wf],
                    'final': self._regs.get(name, BitVec(1, 0)).to_int()
                }

        return results
