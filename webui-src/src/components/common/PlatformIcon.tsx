import { Platform } from '../../types';

import xhsIcon from '../../assets/platform-icons/xhs.svg';
import dyIcon from '../../assets/platform-icons/dy.svg';
import biliIcon from '../../assets/platform-icons/bili.svg';
import wbIcon from '../../assets/platform-icons/wb.svg';
import wechatIcon from '../../assets/platform-icons/wechat.svg';
import zhihuIcon from '../../assets/platform-icons/zhihu.svg';
import tiebaIcon from '../../assets/platform-icons/tieba.svg';
import ksIcon from '../../assets/platform-icons/ks.svg';

// 品牌色背景（每个图标用官方品牌色做浅色背景）
const PLATFORM_CONFIG: Record<Platform, { icon: string; bg: string; name: string }> = {
  xhs:    { icon: xhsIcon,    bg: '#FF244215', name: '小红书' },
  dy:     { icon: dyIcon,     bg: '#00000010', name: '抖音' },
  bili:   { icon: biliIcon,   bg: '#00A1D615', name: 'B站' },
  wb:     { icon: wbIcon,     bg: '#E6162D15', name: '微博' },
  wechat: { icon: wechatIcon, bg: '#07C16015', name: '微信公众号' },
  zhihu:  { icon: zhihuIcon,  bg: '#0084FF15', name: '知乎' },
  tieba:  { icon: tiebaIcon,  bg: '#2932E115', name: '贴吧' },
  ks:     { icon: ksIcon,     bg: '#FF490615', name: '快手' },
};

interface PlatformIconProps {
  platformId: Platform;
  size?: number;
  /** 是否显示圆角色块背景（默认 false，直接展示 SVG） */
  withBackground?: boolean;
  className?: string;
}

export function PlatformIcon({
  platformId,
  size = 32,
  withBackground = false,
  className = '',
}: PlatformIconProps) {
  const cfg = PLATFORM_CONFIG[platformId];
  if (!cfg) return null;

  const imgEl = (
    <img
      src={cfg.icon}
      alt={cfg.name}
      width={withBackground ? size * 0.6 : size}
      height={withBackground ? size * 0.6 : size}
      style={{ display: 'block' }}
    />
  );

  if (withBackground) {
    return (
      <span
        className={`inline-flex items-center justify-center flex-shrink-0 rounded-xl ${className}`}
        style={{ width: size, height: size, backgroundColor: cfg.bg }}
      >
        {imgEl}
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center justify-center flex-shrink-0 ${className}`}>
      {imgEl}
    </span>
  );
}
