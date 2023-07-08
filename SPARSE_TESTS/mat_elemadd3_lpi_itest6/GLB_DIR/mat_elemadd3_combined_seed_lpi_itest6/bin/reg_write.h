

static void bitstream_glb_config()
{
glb_reg_write(0xe8, 0x1);
glb_reg_write(0xec, 0x0);
glb_reg_write(0xf0, 0xfa);
glb_reg_write(0xf4, 0x14);
glb_reg_write(0x1f4, 0x28);
glb_reg_write(0x2f4, 0x28);
glb_reg_write(0x3f4, 0x28);
glb_reg_write(0x4f4, 0x28);
glb_reg_write(0x5f4, 0x28);
glb_reg_write(0x6f4, 0x28);
glb_reg_write(0x7f4, 0x28);
glb_reg_write(0x8f4, 0x28);
glb_reg_write(0x9f4, 0x28);
}


static void app_glb_config()
{
glb_reg_write(0x78, 0x29);
glb_reg_write(0x7c, 0x1);
glb_reg_write(0x80, 0x0);
glb_reg_write(0x84, 0x0);
glb_reg_write(0x88, 0xd);
glb_reg_write(0x90, 0x1);
glb_reg_write(0x8c, 0x2);
glb_reg_write(0x178, 0x29);
glb_reg_write(0x17c, 0x1);
glb_reg_write(0x180, 0x40000);
glb_reg_write(0x184, 0x0);
glb_reg_write(0x188, 0x29);
glb_reg_write(0x190, 0x1);
glb_reg_write(0x18c, 0x2);
glb_reg_write(0x278, 0x29);
glb_reg_write(0x27c, 0x1);
glb_reg_write(0x280, 0x80000);
glb_reg_write(0x284, 0x0);
glb_reg_write(0x288, 0x29);
glb_reg_write(0x290, 0x1);
glb_reg_write(0x28c, 0x2);
glb_reg_write(0x378, 0x29);
glb_reg_write(0x37c, 0x1);
glb_reg_write(0x380, 0xc0000);
glb_reg_write(0x384, 0x0);
glb_reg_write(0x388, 0x29);
glb_reg_write(0x390, 0x1);
glb_reg_write(0x38c, 0x2);
glb_reg_write(0x478, 0x29);
glb_reg_write(0x47c, 0x1);
glb_reg_write(0x480, 0x100000);
glb_reg_write(0x484, 0x0);
glb_reg_write(0x488, 0xd);
glb_reg_write(0x490, 0x1);
glb_reg_write(0x48c, 0x2);
glb_reg_write(0x578, 0x29);
glb_reg_write(0x57c, 0x1);
glb_reg_write(0x580, 0x140000);
glb_reg_write(0x584, 0x0);
glb_reg_write(0x588, 0xd);
glb_reg_write(0x590, 0x1);
glb_reg_write(0x58c, 0x2);
glb_reg_write(0x678, 0x29);
glb_reg_write(0x67c, 0x1);
glb_reg_write(0x680, 0x180000);
glb_reg_write(0x684, 0x0);
glb_reg_write(0x688, 0x1c);
glb_reg_write(0x690, 0x1);
glb_reg_write(0x68c, 0x2);
glb_reg_write(0x778, 0x29);
glb_reg_write(0x77c, 0x1);
glb_reg_write(0x780, 0x1c0000);
glb_reg_write(0x784, 0x0);
glb_reg_write(0x788, 0x1c);
glb_reg_write(0x790, 0x1);
glb_reg_write(0x78c, 0x2);
glb_reg_write(0x878, 0x29);
glb_reg_write(0x87c, 0x1);
glb_reg_write(0x880, 0x200000);
glb_reg_write(0x884, 0x0);
glb_reg_write(0x888, 0x1c);
glb_reg_write(0x890, 0x1);
glb_reg_write(0x88c, 0x2);
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
