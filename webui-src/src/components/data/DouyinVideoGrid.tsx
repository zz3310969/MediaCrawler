import { Play, Heart } from 'lucide-react';
import { DouyinVideo } from '../../types';
import { formatNumber } from '../../lib/utils';

interface DouyinVideoGridProps {
  videos: DouyinVideo[];
}

export function DouyinVideoGrid({ videos }: DouyinVideoGridProps) {
  return (
    <div className="grid grid-cols-4 gap-4">
      {videos.map((video) => (
        <div
          key={video.id}
          className="relative rounded-xl overflow-hidden cursor-pointer group"
          style={{ aspectRatio: '9/16', maxHeight: '280px' }}
        >
          {/* 封面背景 */}
          <div
            className="absolute inset-0"
            style={{
              backgroundColor: getVideoColor(video.id),
            }}
          >
            {video.cover && (
              <img
                src={video.cover}
                alt={video.title}
                className="w-full h-full object-cover"
              />
            )}
          </div>

          {/* 作者标签 */}
          <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 bg-black/50 rounded-full">
            <div className="w-5 h-5 rounded-full bg-slate-300 overflow-hidden">
              {video.author.avatar && (
                <img
                  src={video.author.avatar}
                  alt={video.author.nickname}
                  className="w-full h-full object-cover"
                />
              )}
            </div>
            <span className="text-xs text-white truncate max-w-[100px]">
              {video.author.nickname}
            </span>
          </div>

          {/* 底部渐变遮罩 */}
          <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/80 to-transparent" />

          {/* 底部信息 */}
          <div className="absolute inset-x-0 bottom-0 p-3 space-y-2">
            <p className="text-xs text-white line-clamp-2">
              {video.title}
            </p>
            <div className="flex items-center gap-3 text-xs text-white/80">
              <span className="flex items-center gap-1">
                <Play className="w-3 h-3" />
                {formatNumber(video.play_count)}
              </span>
              <span className="flex items-center gap-1">
                <Heart className="w-3 h-3" />
                {formatNumber(video.like_count)}
              </span>
            </div>
          </div>

          {/* 播放按钮悬浮层 */}
          <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="w-12 h-12 rounded-full bg-white/30 flex items-center justify-center">
              <Play className="w-6 h-6 text-white" fill="white" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// 根据 ID 生成随机视频背景颜色
function getVideoColor(id: string): string {
  const colors = [
    '#0D0D0D', '#1E3A5F', '#4C1D95', '#7C3AED', '#1F2937', '#374151',
  ];
  const index = id.charCodeAt(0) % colors.length;
  return colors[index];
}
