

static void bitstream_glb_config()
{
glb_reg_write(0xe8, 0x1);
glb_reg_write(0xec, 0x0);
glb_reg_write(0xf0, 0xae);
glb_reg_write(0xf4, 0x14);
glb_reg_write(0x2f4, 0x28);
glb_reg_write(0x4f4, 0x28);
glb_reg_write(0x6f4, 0x28);
glb_reg_write(0x8f4, 0x28);
glb_reg_write(0xaf4, 0x28);
}


static void app_glb_config()
{
glb_reg_write(0x78, 0x29);
glb_reg_write(0x7c, 0x1);
glb_reg_write(0x80, 0x0);
glb_reg_write(0x84, 0x0);
glb_reg_write(0x88, 0x15);
glb_reg_write(0x90, 0x1);
glb_reg_write(0x8c, 0x2);
glb_reg_write(0x278, 0x29);
glb_reg_write(0x27c, 0x1);
glb_reg_write(0x280, 0x40000);
glb_reg_write(0x284, 0x0);
glb_reg_write(0x288, 0x65);
glb_reg_write(0x290, 0x1);
glb_reg_write(0x28c, 0x2);
glb_reg_write(0x478, 0x29);
glb_reg_write(0x47c, 0x1);
glb_reg_write(0x480, 0x80000);
glb_reg_write(0x484, 0x0);
glb_reg_write(0x488, 0x65);
glb_reg_write(0x490, 0x1);
glb_reg_write(0x48c, 0x2);
glb_reg_write(0x678, 0x29);
glb_reg_write(0x67c, 0x1);
glb_reg_write(0x680, 0xc0000);
glb_reg_write(0x684, 0x0);
glb_reg_write(0x688, 0x15);
glb_reg_write(0x690, 0x1);
glb_reg_write(0x68c, 0x2);
glb_reg_write(0x878, 0x29);
glb_reg_write(0x87c, 0x1);
glb_reg_write(0x880, 0x100000);
glb_reg_write(0x884, 0x0);
glb_reg_write(0x888, 0x50);
glb_reg_write(0x890, 0x1);
glb_reg_write(0x88c, 0x2);
glb_reg_write(0xa78, 0x29);
glb_reg_write(0xa7c, 0x1);
glb_reg_write(0xa80, 0x140000);
glb_reg_write(0xa84, 0x0);
glb_reg_write(0xa88, 0x50);
glb_reg_write(0xa90, 0x1);
glb_reg_write(0xa8c, 0x2);
glb_reg_write(0x10, 0x25);
glb_reg_write(0x14, 0x2);
glb_reg_write(0x18, 0x1);
glb_reg_write(0x1c, 0x20000);
glb_reg_write(0x20, 0x0);
glb_reg_write(0x24, 0x3fe);
glb_reg_write(0x2c, 0x1);
glb_reg_write(0x28, 0x2);
glb_reg_write(0x210, 0x25);
glb_reg_write(0x214, 0x2);
glb_reg_write(0x218, 0x1);
glb_reg_write(0x21c, 0x60000);
glb_reg_write(0x220, 0x0);
glb_reg_write(0x224, 0x3fe);
glb_reg_write(0x22c, 0x1);
glb_reg_write(0x228, 0x2);
glb_reg_write(0x410, 0x25);
glb_reg_write(0x414, 0x1);
glb_reg_write(0x418, 0x1);
glb_reg_write(0x41c, 0xa0000);
glb_reg_write(0x420, 0x0);
glb_reg_write(0x424, 0x3fe);
glb_reg_write(0x42c, 0x1);
glb_reg_write(0x428, 0x2);
}
