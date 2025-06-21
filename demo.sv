
//DEMO variable
wire [16-1:0] data = 16'b0;
logic [31:0] buffer[8];

wire alu_vld = 0;

	assign alu = 1;
	assign lsu = 1;
	assign fsu = 1;

assign value_1 = 0;
assign value_2 = 0;
assign value_3 = 0;
assign value_4 = 0;
assign value_5 = 0;
assign value_6 = 0;


//DEMO: FOR
	assign value_0 = 0 * 1;
	assign value_0 = 0 * 2;
	assign value_1 = 1 * 1;
	assign value_2 = 1 * 2;

//DEMO: IF
//cond1:
	assign if_match = a < b;
//cond2:
	assign else_match = a < b;
//cond3:
	assign elsif_match1 = a != b;




//DEMO: IF condition
//cond1:
// + - * // % is all ok 
	assign if_match = cmp_a + cmp_b == 8;
//cond2:
// > < >= <= != == is all ok
// & && | || or and is ok
	assign if_match = cmp_a !=0 and cmp_b !=0;
//cond3:
// ~ ! not is all ok
	assign if_match = cmp_a ==3;
//cond4:
	assign test[0][0] = 1;



//DEMO: variable overwrite 
//DEMO: nested if or for

   assign 1 + 2;
   assign 101
   assign compare
   assign 2 + 2;
   assign 102
   assign compare
   assign 0 + 2;
   assign 100
   assign 1 + 2;
   assign 101
   assign 2 + 2;
   assign 102
   assign 0 + 2;
   assign 100
   assign 1 + 2;
   assign 101
   assign 2 + 2;
   assign 102
   assign 0 + 2;
   assign 100
   assign 1 + 2;
   assign 101
   assign compare
   assign 2 + 2;
   assign 102
   assign compare
   assign 0 + 2;
   assign 100
   assign 1 + 2;
   assign 101
   assign 2 + 2;
   assign 102
   assign 0 + 2;
   assign 100
   assign 1 + 2;
   assign 101
   assign 2 + 2;
   assign 102
   assign 0 + 2;
   assign 100
   assign 1 + 2;
   assign 101
   assign compare
   assign 2 + 2;
   assign 102
   assign compare
   assign 0 + 2;
   assign 100
   assign 1 + 2;
   assign 101
   assign 2 + 2;
   assign 102
   assign 0 + 2;
   assign 100
   assign 1 + 2;
   assign 101
   assign 2 + 2;
   assign 102
   assign 0 + 2;
   assign 100

assign alu= 5

   assign 5 < 10;
   assign 0
   assign 1
   assign 2
   assign 3
   assign 4
   assign 5
   assign 6
   assign 7
   assign 8
   assign 9
