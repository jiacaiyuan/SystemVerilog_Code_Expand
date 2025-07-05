`include "macro_demo_nest.svh"       //if same directory can auto include, else ignore
`define RID_WIDTH   9                //can use ${RID_WIDTH}
`define RID_MSB     `RID_WIDTH-1     //can use ${RID_MSB}
`define RID_RINGE   `RID_WIDTH-1:0
//`define XYZ       1
/*`define ABC       2*/

`define CFG_ENA   //ENABLE 

`ifdef CFG_ENA
`define ENABLE_FEAT 1
`else
`define ENABLE_FEAT 0
`endif 

`define FUNC(a,b) a+b

