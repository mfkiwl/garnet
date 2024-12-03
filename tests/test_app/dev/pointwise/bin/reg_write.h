

static void bitstream_glb_config()
{
glb_reg_write(0xec, 0x1);
glb_reg_write(0xf0, 0x0);
glb_reg_write(0xf4, 0x43);
glb_reg_write(0xf8, 0x14);
glb_reg_write(0x4f8, 0x28);
glb_reg_write(0x8f8, 0x28);
glb_reg_write(0xcf8, 0x28);
}


static void app_glb_config()
{
glb_reg_write(0x7c, 0x21);
glb_reg_write(0x80, 0x1);
glb_reg_write(0x84, 0x0);
glb_reg_write(0x88, 0x0);
glb_reg_write(0x8c, 0xffe);
glb_reg_write(0x94, 0x1);
glb_reg_write(0x90, 0x2);
glb_reg_write(0x10, 0x21);
glb_reg_write(0x14, 0x1);
glb_reg_write(0x18, 0x1);
glb_reg_write(0x1c, 0x1);
glb_reg_write(0x20, 0x10000);
glb_reg_write(0x24, 0x4);
glb_reg_write(0x28, 0xffe);
glb_reg_write(0x30, 0x1);
glb_reg_write(0x2c, 0x2);
}
