# -*- coding: utf-8 -*-
# @Desc    : 浏览器指纹随机化

import hashlib
import json
import random
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


@dataclass
class BrowserFingerprint:
    """浏览器指纹数据模型"""

    # 唯一标识
    fingerprint_id: str = ""

    # User Agent
    user_agent: str = ""

    # 视口和屏幕
    viewport_width: int = 1920
    viewport_height: int = 1080
    screen_width: int = 1920
    screen_height: int = 1080
    color_depth: int = 24
    pixel_ratio: float = 1.0

    # 系统信息
    platform: str = "MacIntel"
    language: str = "zh-CN"
    languages: List[str] = field(default_factory=lambda: ["zh-CN", "zh", "en"])
    timezone: str = "Asia/Shanghai"
    timezone_offset: int = -480  # 分钟，北京时间 UTC+8

    # WebGL
    webgl_vendor: str = ""
    webgl_renderer: str = ""

    # Canvas 指纹
    canvas_hash: str = ""

    # 硬件信息
    hardware_concurrency: int = 8  # CPU 核心数
    device_memory: int = 8  # GB

    # 其他
    do_not_track: Optional[str] = None  # "1", None, "unspecified"

    def __post_init__(self):
        """生成指纹ID"""
        if not self.fingerprint_id:
            # 基于关键属性生成唯一ID
            key_str = f"{self.user_agent}{self.screen_width}{self.screen_height}{self.webgl_renderer}"
            self.fingerprint_id = hashlib.md5(key_str.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "BrowserFingerprint":
        """从字典创建"""
        return cls(**data)


class FingerprintGenerator:
    """浏览器指纹生成器"""

    # 真实的 User Agent 列表（2024-2025年常见版本）
    USER_AGENTS = [
        # macOS Chrome
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",

        # Windows Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",

        # macOS Edge
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",

        # Windows Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]

    # 常见分辨率（按使用率排序）
    VIEWPORTS = [
        (1920, 1080),  # Full HD
        (1366, 768),   # 笔记本常见
        (1536, 864),   # 1.5倍缩放
        (1440, 900),   # MacBook
        (2560, 1440),  # 2K
        (1280, 720),   # HD
        (1600, 900),   # HD+
    ]

    # WebGL 配置（真实硬件）
    WEBGL_CONFIGS = [
        # Intel 集成显卡
        ("Intel Inc.", "Intel Iris OpenGL Engine"),
        ("Intel Inc.", "Intel(R) UHD Graphics 630"),
        ("Intel Inc.", "Intel(R) Iris(R) Plus Graphics 640"),

        # NVIDIA 独显
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0)"),
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"),

        # AMD 显卡
        ("Google Inc. (AMD)", "ANGLE (AMD Radeon Pro 5500M Direct3D11 vs_5_0 ps_5_0)"),
        ("Google Inc. (AMD)", "ANGLE (AMD Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0)"),
    ]

    # CPU 核心数分布
    CPU_CORES = [4, 6, 8, 8, 8, 12, 16]  # 8核最常见

    # 内存大小分布 (GB)
    MEMORY_SIZES = [8, 8, 16, 16, 16, 32]  # 8GB和16GB最常见

    @classmethod
    def generate(cls, platform_hint: Optional[str] = None) -> BrowserFingerprint:
        """
        生成随机但真实的浏览器指纹

        Args:
            platform_hint: 平台提示 ("mac", "windows", "linux")，为空则随机

        Returns:
            BrowserFingerprint: 生成的指纹
        """
        # 选择 User Agent
        if platform_hint:
            platform_hint = platform_hint.lower()
            filtered_uas = [ua for ua in cls.USER_AGENTS if platform_hint in ua.lower()]
            user_agent = random.choice(filtered_uas) if filtered_uas else random.choice(cls.USER_AGENTS)
        else:
            user_agent = random.choice(cls.USER_AGENTS)

        # 根据 UA 确定平台
        if "Mac" in user_agent:
            platform = "MacIntel"
        elif "Windows" in user_agent:
            platform = "Win32"
        elif "Linux" in user_agent:
            platform = "Linux x86_64"
        else:
            platform = "Win32"

        # 选择分辨率
        viewport_width, viewport_height = random.choice(cls.VIEWPORTS)

        # 屏幕分辨率通常大于等于视口
        screen_width = viewport_width + random.randint(0, 200)
        screen_height = viewport_height + random.randint(0, 150)

        # 像素比（Mac 通常是 2.0，Windows 通常是 1.0 或 1.25）
        if platform == "MacIntel":
            pixel_ratio = random.choice([2.0, 2.0, 2.0, 1.0])  # Mac 大多是 Retina
        else:
            pixel_ratio = random.choice([1.0, 1.0, 1.25, 1.5])

        # WebGL 配置
        webgl_vendor, webgl_renderer = random.choice(cls.WEBGL_CONFIGS)

        # 硬件信息
        hardware_concurrency = random.choice(cls.CPU_CORES)
        device_memory = random.choice(cls.MEMORY_SIZES)

        # 颜色深度
        color_depth = random.choice([24, 24, 24, 32])  # 24位最常见

        # Do Not Track（大多数用户不设置）
        do_not_track = random.choices(
            [None, "1", "unspecified"],
            weights=[0.7, 0.2, 0.1],
            k=1
        )[0]

        return BrowserFingerprint(
            user_agent=user_agent,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            screen_width=screen_width,
            screen_height=screen_height,
            color_depth=color_depth,
            pixel_ratio=pixel_ratio,
            platform=platform,
            webgl_vendor=webgl_vendor,
            webgl_renderer=webgl_renderer,
            hardware_concurrency=hardware_concurrency,
            device_memory=device_memory,
            do_not_track=do_not_track,
        )

    @classmethod
    def to_playwright_args(cls, fp: BrowserFingerprint) -> Dict:
        """
        转换为 Playwright 启动参数

        Args:
            fp: 浏览器指纹

        Returns:
            Dict: Playwright context 参数
        """
        return {
            "user_agent": fp.user_agent,
            "viewport": {
                "width": fp.viewport_width,
                "height": fp.viewport_height,
            },
            "screen": {
                "width": fp.screen_width,
                "height": fp.screen_height,
            },
            "device_scale_factor": fp.pixel_ratio,
            "locale": fp.language,
            "timezone_id": fp.timezone,
        }

    @classmethod
    def to_init_script(cls, fp: BrowserFingerprint) -> str:
        """
        生成注入脚本，覆盖浏览器指纹

        Args:
            fp: 浏览器指纹

        Returns:
            str: JavaScript 注入脚本
        """
        return f"""
        (() => {{
            // 覆盖 navigator 属性
            Object.defineProperty(navigator, 'webdriver', {{
                get: () => undefined,
                configurable: true
            }});

            Object.defineProperty(navigator, 'platform', {{
                get: () => '{fp.platform}',
                configurable: true
            }});

            Object.defineProperty(navigator, 'language', {{
                get: () => '{fp.language}',
                configurable: true
            }});

            Object.defineProperty(navigator, 'languages', {{
                get: () => {json.dumps(fp.languages)},
                configurable: true
            }});

            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {fp.hardware_concurrency},
                configurable: true
            }});

            Object.defineProperty(navigator, 'deviceMemory', {{
                get: () => {fp.device_memory},
                configurable: true
            }});

            {f"Object.defineProperty(navigator, 'doNotTrack', {{get: () => '{fp.do_not_track}', configurable: true}});" if fp.do_not_track else ""}

            // 覆盖 screen 属性
            Object.defineProperty(screen, 'width', {{
                get: () => {fp.screen_width},
                configurable: true
            }});

            Object.defineProperty(screen, 'height', {{
                get: () => {fp.screen_height},
                configurable: true
            }});

            Object.defineProperty(screen, 'colorDepth', {{
                get: () => {fp.color_depth},
                configurable: true
            }});

            Object.defineProperty(screen, 'pixelDepth', {{
                get: () => {fp.color_depth},
                configurable: true
            }});

            // 覆盖 devicePixelRatio
            Object.defineProperty(window, 'devicePixelRatio', {{
                get: () => {fp.pixel_ratio},
                configurable: true
            }});

            // 覆盖 WebGL
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {{
                if (param === 37445) {{
                    return '{fp.webgl_vendor}';
                }}
                if (param === 37446) {{
                    return '{fp.webgl_renderer}';
                }}
                return getParameter.call(this, param);
            }};

            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(param) {{
                if (param === 37445) {{
                    return '{fp.webgl_vendor}';
                }}
                if (param === 37446) {{
                    return '{fp.webgl_renderer}';
                }}
                return getParameter2.call(this, param);
            }};

            // 添加 Chrome 对象（如果不存在）
            if (!window.chrome) {{
                window.chrome = {{
                    runtime: {{}},
                    loadTimes: function() {{}},
                    csi: function() {{}},
                    app: {{}}
                }};
            }}

            // 伪装插件
            Object.defineProperty(navigator, 'plugins', {{
                get: () => {{
                    const plugins = [
                        {{
                            name: 'Chrome PDF Plugin',
                            filename: 'internal-pdf-viewer',
                            description: 'Portable Document Format'
                        }},
                        {{
                            name: 'Chrome PDF Viewer',
                            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                            description: 'Portable Document Format'
                        }},
                        {{
                            name: 'Native Client',
                            filename: 'internal-nacl-plugin',
                            description: 'Native Client Executable'
                        }}
                    ];
                    plugins.length = 3;
                    return plugins;
                }},
                configurable: true
            }});

            // 覆盖 permissions API（防止检测）
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({{ state: Notification.permission }}) :
                    originalQuery(parameters)
            );

            // 移除自动化痕迹
            delete navigator.__proto__.webdriver;

            console.log('[AntiDetect] Fingerprint injected:', '{fp.fingerprint_id}');
        }})();
        """


class FingerprintStore:
    """指纹持久化存储"""

    def __init__(self, storage_path: str = "data/fingerprints.json"):
        """
        初始化指纹存储

        Args:
            storage_path: 存储文件路径
        """
        self.storage_path = storage_path
        self._fingerprints: Dict[str, BrowserFingerprint] = {}
        self._load()

    def _load(self):
        """从文件加载指纹"""
        import os
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for fp_id, fp_data in data.items():
                        self._fingerprints[fp_id] = BrowserFingerprint.from_dict(fp_data)
            except Exception as e:
                print(f"[FingerprintStore] Failed to load fingerprints: {e}")

    def _save(self):
        """保存指纹到文件"""
        import os
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            data = {fp_id: fp.to_dict() for fp_id, fp in self._fingerprints.items()}
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[FingerprintStore] Failed to save fingerprints: {e}")

    def get(self, fingerprint_id: str) -> Optional[BrowserFingerprint]:
        """获取指纹"""
        return self._fingerprints.get(fingerprint_id)

    def save(self, fingerprint: BrowserFingerprint):
        """保存指纹"""
        self._fingerprints[fingerprint.fingerprint_id] = fingerprint
        self._save()

    def delete(self, fingerprint_id: str):
        """删除指纹"""
        if fingerprint_id in self._fingerprints:
            del self._fingerprints[fingerprint_id]
            self._save()

    def list_all(self) -> List[BrowserFingerprint]:
        """列出所有指纹"""
        return list(self._fingerprints.values())
