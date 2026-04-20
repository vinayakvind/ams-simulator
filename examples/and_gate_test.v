// Simple AND gate testbench
module and_test;
    wire a, b, out;
    
    // AND gate
    and g1(out, a, b);
    
    // Test inputs
    initial begin
        a = 0;
        b = 0;
        #10 a = 1;
        #10 b = 1;
        #10 a = 0;
        #10 $finish;
    end
endmodule
