from micropython import const
import framebuf


# Register definitions
SET_CONTRAST = const(0x81)
SET_ENTIRE_ON = const(0xa4)
SET_NORM_INV = const(0xa6)
SET_DISP = const(0xae)
SET_MEM_ADDR = const(0x20)
SET_COL_ADDR = const(0x21)
SET_PAGE_ADDR = const(0x22)
SET_DISP_START_LINE = const(0x40)
SET_SEG_REMAP = const(0xa0)
SET_MUX_RATIO = const(0xa8)
SET_COM_OUT_DIR = const(0xc0)
SET_DISP_OFFSET = const(0xd3)
SET_COM_PIN_CFG = const(0xda)
SET_DISP_CLK_DIV = const(0xd5)
SET_PRECHARGE = const(0xd9)
SET_VCOM_DESEL = const(0xdb)
SET_CHARGE_PUMP = const(0x8d)


class Oled(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)

        # Setup the framebuffer - inheritence doesn't work
        self.framebuffer = framebuf.FrameBuffer(
            self.buffer,
            self.width,
            self.height,
            framebuf.MONO_VLSB
        )

        self.fill = self.framebuffer.fill
        self.pixel = self.framebuffer.pixel
        self.hline = self.framebuffer.hline
        self.vline = self.framebuffer.vline
        self.line = self.framebuffer.line
        self.rect = self.framebuffer.rect
        self.fill_rect = self.framebuffer.fill_rect
        self.text = self.framebuffer.text
        self.scroll = self.framebuffer.scroll
        self.blit = self.framebuffer.blit

        self.init_display()

    def init_display(self):
        for cmd in (
            SET_DISP | 0x00,

            # Address setting
            SET_MEM_ADDR, 0x00,

            # Resolution and layout
            SET_DISP_START_LINE | 0x00,
            SET_SEG_REMAP | 0x01,
            SET_MUX_RATIO, self.height - 1,
            SET_COM_OUT_DIR | 0x08,
            SET_DISP_OFFSET, 0x00,
            SET_COM_PIN_CFG, 0x02 if self.height == 32 else 0x12,

            # Timing and driving scheme
            SET_DISP_CLK_DIV, 0x80,
            SET_PRECHARGE, 0xf1,
            SET_VCOM_DESEL, 0x30,

            # Display
            SET_CONTRAST, 0xff,
            SET_ENTIRE_ON,
            SET_NORM_INV,

            # Charge pump
            SET_CHARGE_PUMP, 0x14,
            SET_DISP | 0x01
        ):
            self.write_cmd(cmd)

        self.fill(0)
        self.show()

    def poweroff(self):
        self.write_cmd(SET_DISP | 0x00)

    def poweron(self):
        self.write_cmd(SET_DISP | 0x01)

    def contrast(self, contrast):
        self.write_cmd(SET_CONTRAST)
        self.write_cmd(contrast)

    def invert(self, invert):
        self.write_cmd(SET_NORM_INV | (invert & 1))

    def show(self):
        x0 = 0
        x1 = self.width - 1

        # Displays with width of 64 pixels are shifted by 32
        if self.width == 64:
            x0 += 32
            x1 += 32

        self.write_cmd(SET_COL_ADDR)
        self.write_cmd(x0)
        self.write_cmd(x1)
        self.write_cmd(SET_PAGE_ADDR)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)
        self.write_data(self.buffer)


class OledI2C(Oled):
    def __init__(self, width, height, i2c, addr=0x3c):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        super().__init__(width, height)

    def write_cmd(self, cmd):
        self.temp[0] = 0x80
        self.temp[1] = cmd

        self.i2c.writeto(self.addr, self.temp)

    def write_data(self, buf):
        self.temp[0] = self.addr << 1
        self.temp[1] = 0x40
        self.i2c.start()
        self.i2c.write(self.temp)
        self.i2c.write(buf)
        self.i2c.stop()
