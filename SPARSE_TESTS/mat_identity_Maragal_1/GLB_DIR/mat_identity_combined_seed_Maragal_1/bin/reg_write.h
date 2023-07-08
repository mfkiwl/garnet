

static void bitstream_glb_config()
{
glb_reg_write(0xe8, 0x1);
glb_reg_write(0xec, 0x0);
glb_reg_write(0xf0, 0x4a);
glb_reg_write(0xf4, 0x14);
glb_reg_write(0x1f4, 0x28);
glb_reg_write(0x2f4, 0x28);
glb_reg_write(0x3f4, 0x28);
}


static void app_glb_config()
{
glb_reg_write(0x78, 0x29);
glb_reg_write(0x7c, 0x1);
glb_reg_write(0x80, 0x0);
glb_reg_write(0x84, 0x0);
glb_reg_write(0x88, 0x22);
glb_reg_write(0x90, 0x1);
glb_reg_write(0x8c, 0x2);
glb_reg_write(0x178, 0x29);
glb_reg_write(0x17c, 0x1);
glb_reg_write(0x180, 0x40000);
glb_reg_write(0x184, 0x0);
glb_reg_write(0x188, 0x10b);
glb_reg_write(0x190, 0x1);
glb_reg_write(0x18c, 0x2);
glb_reg_write(0x278, 0x29);
glb_reg_write(0x27c, 0x1);
glb_reg_write(0x280, 0x80000);
glb_reg_write(0x284, 0x0);
glb_reg_write(0x288, 0xe9);
glb_reg_write(0x290, 0x1);
glb_reg_write(0x28c, 0x2);
glb_reg_write(0x10, 0x25);
glb_reg_write(0x14, 0x2);
glb_reg_write(0x18, 0x1);
glb_reg_write(0x1c, 0x20000);
glb_reg_write(0x20, 0x0);
glb_reg_write(0x24, 0x3fe);
glb_reg_write(0x2c, 0x1);
glb_reg_write(0x28, 0x2);
glb_reg_write(0x110, 0x25);
glb_reg_write(0x114, 0x2);
glb_reg_write(0x118, 0x1);
glb_reg_write(0x11c, 0x60000);
glb_reg_write(0x120, 0x0);
glb_reg_write(0x124, 0x3fe);
glb_reg_write(0x12c, 0x1);
glb_reg_write(0x128, 0x2);
glb_reg_write(0x210, 0x25);
glb_reg_write(0x214, 0x1);
glb_reg_write(0x218, 0x1);
glb_reg_write(0x21c, 0xa0000);
glb_reg_write(0x220, 0x0);
glb_reg_write(0x224, 0x3fe);
glb_reg_write(0x22c, 0x1);
glb_reg_write(0x228, 0x2);
}
