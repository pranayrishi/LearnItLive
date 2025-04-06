from manim import *

class RaspberryPi4BOverview(Scene):
    def construct(self):
        # Title
        title = Text("Raspberry Pi 4B - PCB Overview", font_size=36).to_edge(UP)
        self.play(Write(title))
        self.wait(1)

        # Draw PCB Board
        pcb = Rectangle(width=6, height=3.5, color=GREEN).shift(DOWN * 0.5)
        self.play(Create(pcb))

        # COMPONENT POSITIONS (relative to pcb center)
        component_data = [
            # (Shape, Label text, Offset, Label position)
            ("cpu", Square(side_length=0.6, fill_color=BLUE, fill_opacity=0.8), "CPU (BCM2711)", LEFT * 1.8 + UP * 0.7, LEFT * 5 + UP * 2),
            ("ram", Square(side_length=0.5, fill_color=PURPLE, fill_opacity=0.8), "RAM", LEFT * 0.9 + UP * 0.7, RIGHT * 4.5 + UP * 2),
            ("usb", VGroup(
                *[Rectangle(width=0.4, height=0.6, fill_color=GRAY, fill_opacity=0.8).shift(LEFT * i * 0.5) for i in range(4)]
            ), "USB Ports", RIGHT * 1.2 + DOWN * 1.3, RIGHT * 4.5 + DOWN * 2),
            ("ethernet", Rectangle(width=0.5, height=0.6, fill_color=ORANGE, fill_opacity=0.8), "Gigabit Ethernet", RIGHT * 2.1 + DOWN * 1.3, RIGHT * 4.5 + DOWN * 0.5),
            ("hdmi", VGroup(
                *[Rectangle(width=0.3, height=0.2, fill_color=YELLOW, fill_opacity=0.8).shift(LEFT * i * 0.4) for i in range(2)]
            ), "2x Micro HDMI", LEFT * 0.7 + DOWN * 1.7, LEFT * 4.5 + DOWN * 2),
            ("gpio", Rectangle(width=0.2, height=1.2, fill_color=BLACK, fill_opacity=0.9), "GPIO Header", RIGHT * 2.6 + UP * 0.7, RIGHT * 4.5 + UP * 0.7),
            ("camera", Rectangle(width=0.3, height=0.15, fill_color=TEAL, fill_opacity=0.8), "Camera Port", LEFT * 1.2 + UP * 1.3, LEFT * 4.5 + UP * 1),
            ("power", Rectangle(width=0.2, height=0.2, fill_color=RED, fill_opacity=0.8), "USB-C Power In", LEFT * 2.5 + DOWN * 1.3, LEFT * 4.5 + DOWN * 0.5),
        ]

        # Animate each component and label
        for name, shape, label_text, shape_offset, label_pos in component_data:
            shape.move_to(pcb.get_center() + shape_offset)
            label = Text(label_text, font_size=18).move_to(label_pos)

            # Draw an arrow from label to shape center
            arrow = Arrow(start=label.get_center(), end=shape.get_center(), buff=0.1, stroke_width=2)
            self.play(FadeIn(shape), Write(label), GrowArrow(arrow))
            self.wait(0.4)

        # MicroSD Note
        sd_text = Text("MicroSD Card Slot (on back side)", font_size=18).next_to(pcb, DOWN)
        self.play(Write(sd_text))
        self.wait(3)

        # Outro
        self.play(*[FadeOut(mob) for mob in self.mobjects])
        outro = Text("That's the Raspberry Pi 4B!", font_size=36)
        self.play(Write(outro))
        self.wait(2)
