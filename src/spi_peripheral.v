`default_nettype none
module spi_peripheral (input clk, input rst_n, input sclk, input ncs, input copi, output reg [7:0]enregout7_0, output reg [7:0]enregout15_8, output reg [7:0]enpwmmode7_0, output reg [7:0]enpwmmode15_8, output reg [7:0]pwmdutycycle);

    // first thing: need the 2-stage flip-flop to synchronise the external and internal clocks
        //declarations for sampling registers
    reg sclk_1;
    reg sclk_2;
    reg sclk_3;
    reg copi_1;
    reg copi_2;
    reg ncs_1;
    reg ncs_2;
        // run every clock cycle
    always@(posedge clk or negedge rst_n) begin
        // reset logic
    if (!rst_n) begin sclk_1<=0; sclk_2<=0; sclk_3<=0; copi_1<=0;copi_2<=0;ncs_1<=0;ncs_2<=0; end 
    else begin
        // sampling 3 times for sclk, 2 times fo copi and ncs.
        sclk_1 <= sclk;
        sclk_2 <= sclk_1;
        sclk_3 <= sclk_2;
        copi_1 <= copi;
        copi_2 <= copi_1;
        ncs_1 <= ncs;
        ncs_2 <= ncs_1;
     end
    end
    // edge detection logic for sclk, ncs
    wire sclk_rising = (sclk_2 ==1) & (sclk_3 ==0);
    wire ncs_posedge = (ncs_1 ==1) & (ncs_2 ==0);

// next, need the block that starts transmission on ncs_2 == 0, does sampling at sclk_rising, does transmission logic, AND transaction logc (edit)
    /* verilator lint_off UNUSEDSIGNAL */
    reg [15:0]shift_reg;
    /* verilator lint_on UNUSEDSIGNAL */
    reg [4:0]count;
      // need a wire for "data", "address" , makes things cleaner
    wire [7:0]data = shift_reg[7:0];
    wire [6:0]address = shift_reg[14:8];


    always@(posedge clk or negedge rst_n)begin 
        // reset block 
        if(!rst_n) begin
            count <= 5'd0;
            shift_reg <= 16'd0;
            enregout7_0 <= 8'd0;
            enregout15_8 <= 8'd0;
            enpwmmode7_0 <= 8'd0;
            enpwmmode15_8 <= 8'd0;
            pwmdutycycle <= 8'd0;
        
        end 
        // TRANSACTION LOGIC PLACED FIRST AFTER ANALYZING GDS WAVEFORM
        else if(ncs_posedge && count == 5'd16) begin

            case(address)
            7'h00 : enregout7_0 <= data ;
            7'h01 : enregout15_8 <= data;
            7'h02 : enpwmmode7_0 <= data;
            7'h03 : enpwmmode15_8 <= data;
            7'h04 : pwmdutycycle <= data;
            default: ;
            endcase
        count <= 5'd0;
        end 
        // TRANSMISSION LOGIC PLACED SECOND AFTER ANALYZING GDS WAVEFORM
        // when ncs_2 = 0 (active low), check if rising edge on sclk, if yes, sample and increment till ncs_2 is 1 (transmision complete)
        else if(!ncs_2) begin
            if(sclk_rising) begin
                 shift_reg[15-count] <= copi_2;
               count <= count+1;
            end
        end 
        end
    
    // second always with transaction logic DELETED, moved into FIRST
  
 endmodule