# -*- coding: utf-8 -*-
# @Desc    : 人类行为模拟器

import asyncio
import math
import random
from typing import Optional, Tuple

from playwright.async_api import Page


class HumanBehaviorSimulator:
    """
    模拟真实用户操作行为

    功能:
    - 非线性滚动（开始快、中间慢、结束快）
    - 贝塞尔曲线鼠标移动
    - 自然的点击行为（移动-停顿-点击）
    - 变速打字
    - 随机浏览行为
    """

    @staticmethod
    async def human_scroll(
        page: Page,
        direction: str = "down",
        distance: Optional[int] = None,
        speed: str = "normal"
    ):
        """
        模拟人类滚动 - 非线性速度

        Args:
            page: Playwright Page 对象
            direction: 滚动方向 ("down" 或 "up")
            distance: 滚动距离（像素），为空则随机
            speed: 滚动速度 ("slow", "normal", "fast")
        """
        if distance is None:
            distance = random.randint(300, 800)

        # 根据速度调整步数
        speed_map = {"slow": (8, 20), "normal": (5, 15), "fast": (3, 8)}
        min_steps, max_steps = speed_map.get(speed, (5, 15))
        steps = random.randint(min_steps, max_steps)

        for i in range(steps):
            # 非线性滚动：开始快、中间慢、结束快（正弦曲线）
            progress = i / steps
            speed_factor = 0.5 + math.sin(progress * math.pi) * 0.5
            step_distance = int(distance / steps * (0.5 + speed_factor))

            if direction == "down":
                await page.mouse.wheel(0, step_distance)
            else:
                await page.mouse.wheel(0, -step_distance)

            # 每步之间的随机延迟
            await asyncio.sleep(random.uniform(0.02, 0.08))

        # 滚动后的短暂停顿（模拟阅读）
        await asyncio.sleep(random.uniform(0.3, 1.0))

    @staticmethod
    async def human_move_to(page: Page, x: int, y: int):
        """
        模拟人类鼠标移动 - 贝塞尔曲线路径

        Args:
            page: Playwright Page 对象
            x: 目标 X 坐标
            y: 目标 Y 坐标
        """
        # 获取当前鼠标位置（如果有记录）
        try:
            current = await page.evaluate("() => ({x: window.mouseX || 0, y: window.mouseY || 0})")
            start_x, start_y = current.get("x", 0), current.get("y", 0)
        except:
            start_x, start_y = 0, 0

        # 如果起点和终点太近，直接移动
        distance = math.sqrt((x - start_x) ** 2 + (y - start_y) ** 2)
        if distance < 10:
            await page.mouse.move(x, y)
            return

        # 生成贝塞尔曲线控制点（添加随机性）
        cp1_x = start_x + (x - start_x) * random.uniform(0.2, 0.4)
        cp1_y = start_y + random.randint(-100, 100)
        cp2_x = start_x + (x - start_x) * random.uniform(0.6, 0.8)
        cp2_y = y + random.randint(-100, 100)

        # 根据距离调整步数
        steps = int(distance / 10) + random.randint(10, 20)
        steps = min(steps, 50)  # 最多50步

        for i in range(steps + 1):
            t = i / steps
            # 三次贝塞尔曲线公式
            px = (
                (1 - t) ** 3 * start_x
                + 3 * (1 - t) ** 2 * t * cp1_x
                + 3 * (1 - t) * t ** 2 * cp2_x
                + t ** 3 * x
            )
            py = (
                (1 - t) ** 3 * start_y
                + 3 * (1 - t) ** 2 * t * cp1_y
                + 3 * (1 - t) * t ** 2 * cp2_y
                + t ** 3 * y
            )

            await page.mouse.move(px, py)

            # 速度变化：中间快两端慢（正弦曲线）
            delay = 0.005 + 0.02 * (1 - math.sin(t * math.pi))
            await asyncio.sleep(delay)

        # 记录鼠标位置
        await page.evaluate(f"() => {{ window.mouseX = {x}; window.mouseY = {y}; }}")

    @staticmethod
    async def human_click(page: Page, selector: str, button: str = "left"):
        """
        模拟人类点击

        Args:
            page: Playwright Page 对象
            selector: 元素选择器
            button: 鼠标按钮 ("left", "right", "middle")
        """
        element = await page.query_selector(selector)
        if not element:
            raise ValueError(f"Element not found: {selector}")

        box = await element.bounding_box()
        if not box:
            raise ValueError(f"Element not visible: {selector}")

        # 点击位置随机偏移（不总是点正中间，更像人类）
        x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
        y = box["y"] + box["height"] * random.uniform(0.3, 0.7)

        # 移动到目标位置
        await HumanBehaviorSimulator.human_move_to(page, int(x), int(y))

        # 移动到位后的短暂犹豫
        await asyncio.sleep(random.uniform(0.05, 0.15))

        # 点击（按下-停顿-抬起）
        await page.mouse.down(button=button)
        await asyncio.sleep(random.uniform(0.05, 0.12))  # 按下时长
        await page.mouse.up(button=button)

        # 点击后停顿
        await asyncio.sleep(random.uniform(0.1, 0.3))

    @staticmethod
    async def human_type(page: Page, selector: str, text: str, clear_first: bool = True):
        """
        模拟人类打字 - 变速输入

        Args:
            page: Playwright Page 对象
            selector: 输入框选择器
            text: 要输入的文本
            clear_first: 是否先清空输入框
        """
        # 点击输入框
        await HumanBehaviorSimulator.human_click(page, selector)

        # 清空输入框
        if clear_first:
            await page.fill(selector, "")

        # 开始打字前的停顿（思考）
        await asyncio.sleep(random.uniform(0.3, 0.8))

        # 逐字符输入
        for i, char in enumerate(text):
            await page.keyboard.press(char)

            # 打字速度变化
            if char == " ":
                # 空格后稍微停顿
                delay = random.uniform(0.1, 0.3)
            elif i > 0 and text[i - 1] in ",.!?;:":
                # 标点后停顿
                delay = random.uniform(0.2, 0.5)
            elif random.random() < 0.05:
                # 偶尔的较长停顿（思考）
                delay = random.uniform(0.3, 0.8)
            else:
                # 正常打字速度
                delay = random.uniform(0.05, 0.15)

            await asyncio.sleep(delay)

        # 打字结束后的停顿
        await asyncio.sleep(random.uniform(0.2, 0.5))

    @staticmethod
    async def random_browse(page: Page, duration: float = 5.0):
        """
        随机浏览行为 - 模拟用户阅读页面

        Args:
            page: Playwright Page 对象
            duration: 浏览时长（秒）
        """
        end_time = asyncio.get_event_loop().time() + duration

        while asyncio.get_event_loop().time() < end_time:
            # 随机选择一个动作
            action = random.choices(
                ["scroll", "move", "pause", "read"],
                weights=[0.3, 0.2, 0.2, 0.3],
                k=1
            )[0]

            if action == "scroll":
                # 滚动（更偏向向下）
                direction = random.choice(["down", "down", "down", "up"])
                await HumanBehaviorSimulator.human_scroll(page, direction)

            elif action == "move":
                # 随机移动鼠标
                viewport = page.viewport_size
                x = random.randint(100, viewport["width"] - 100)
                y = random.randint(100, viewport["height"] - 100)
                await HumanBehaviorSimulator.human_move_to(page, x, y)

            elif action == "pause":
                # 停顿（模拟思考）
                await asyncio.sleep(random.uniform(1.0, 3.0))

            elif action == "read":
                # 模拟阅读：小幅滚动 + 长停顿
                await HumanBehaviorSimulator.human_scroll(
                    page, "down", random.randint(50, 200), speed="slow"
                )
                await asyncio.sleep(random.uniform(2.0, 5.0))

    @staticmethod
    async def hover_element(page: Page, selector: str):
        """
        悬停在元素上

        Args:
            page: Playwright Page 对象
            selector: 元素选择器
        """
        element = await page.query_selector(selector)
        if not element:
            return

        box = await element.bounding_box()
        if not box:
            return

        # 移动到元素中心附近
        x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
        y = box["y"] + box["height"] * random.uniform(0.3, 0.7)

        await HumanBehaviorSimulator.human_move_to(page, int(x), int(y))
        await asyncio.sleep(random.uniform(0.5, 1.5))

    @staticmethod
    async def scroll_to_element(page: Page, selector: str):
        """
        滚动到元素可见

        Args:
            page: Playwright Page 对象
            selector: 元素选择器
        """
        element = await page.query_selector(selector)
        if not element:
            return

        # 先滚动到元素附近
        await element.scroll_into_view_if_needed()

        # 再随机滚动一点（不要正好在顶部）
        offset = random.randint(-100, 100)
        await page.mouse.wheel(0, offset)

        await asyncio.sleep(random.uniform(0.3, 0.8))

    @staticmethod
    async def wait_for_page_load(page: Page, timeout: float = 30.0):
        """
        等待页面加载完成（模拟人类等待）

        Args:
            page: Playwright Page 对象
            timeout: 超时时间（秒）
        """
        try:
            # 等待网络空闲
            await page.wait_for_load_state("networkidle", timeout=timeout * 1000)
        except:
            pass

        # 加载后的短暂停顿（模拟人类反应时间）
        await asyncio.sleep(random.uniform(0.5, 1.5))
