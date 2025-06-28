
//DEMO variable
wire [16-1:0] data = 16'b0;
logic [31:0] buffer[8][16];


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
	assign if_match = cmp_a !=5 and cmp_b !=3;
//cond3:
// ~ ! not is all ok
	assign if_match = cmp_a ==3;
//cond4:
	assign test[0][0] = 1;



//DEMO: variable overwrite 
//DEMO: nested if or for
   assign alu = 101 ;
	assign else_match = 0 != 1;


   assign alu = 102 ;
	assign else_match = 0 != 2;


   assign alu = 100 ;
	assign else_match = 0 != 3;


   assign alu = 101 ;
	assign else_match = 0 != 4;


   assign alu = 102 ;
	assign else_match = 0 != 5;


   assign alu = 100 ;
	assign else_match = 0 != 6;


   assign alu = 101 ;
	assign else_match = 0 != 7;


   assign alu = 102 ;
	assign else_match = 0 != 8;


   assign alu = 100 ;
	assign else_match = 0 != 9;


   assign alu = 101 ;
	assign if_match = 1 == 1;


   assign alu = 102 ;
	assign else_match = 1 != 2;


   assign alu = 100 ;
	assign else_match = 1 != 3;


   assign alu = 101 ;
	assign else_match = 1 != 4;


   assign alu = 102 ;
	assign else_match = 1 != 5;


   assign alu = 100 ;
	assign else_match = 1 != 6;


   assign alu = 101 ;
	assign else_match = 1 != 7;


   assign alu = 102 ;
	assign else_match = 1 != 8;


   assign alu = 100 ;
	assign else_match = 1 != 9;


   assign alu = 101 ;
	assign elsif_match = 2 = 1 + 1;


   assign alu = 102 ;
	assign if_match = 2 == 2;


   assign alu = 100 ;
	assign else_match = 2 != 3;


   assign alu = 101 ;
	assign else_match = 2 != 4;


   assign alu = 102 ;
	assign else_match = 2 != 5;


   assign alu = 100 ;
	assign else_match = 2 != 6;


   assign alu = 101 ;
	assign else_match = 2 != 7;


   assign alu = 102 ;
	assign else_match = 2 != 8;


   assign alu = 100 ;
	assign else_match = 2 != 9;


  
  
  

assign alu= 5



   assign 5 != 10;
   assign 0
   assign 1
   assign 2
   assign 3
   assign 4



******************************************


   assign 5 != 10;
   
   assign 5 != 10;





finish 
