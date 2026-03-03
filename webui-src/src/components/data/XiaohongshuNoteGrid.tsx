import { Heart, MessageCircle, Bookmark } from 'lucide-react';
import { XiaohongshuNote } from '../../types';
import { formatNumber } from '../../lib/utils';

interface XiaohongshuNoteGridProps {
  notes: XiaohongshuNote[];
}

export function XiaohongshuNoteGrid({ notes }: XiaohongshuNoteGridProps) {
  return (
    <div className="grid grid-cols-4 gap-5">
      {notes.map((note) => (
        <div
          key={note.id}
          className="bg-white rounded-lg border border-border overflow-hidden hover:shadow-card-hover transition-shadow cursor-pointer"
        >
          {/* 封面 */}
          <div
            className="relative aspect-[4/3] bg-slate-100"
            style={{
              backgroundColor: note.cover ? undefined : getRandomColor(note.id),
            }}
          >
            {note.cover && (
              <img
                src={note.cover}
                alt={note.title}
                className="w-full h-full object-cover"
              />
            )}
            {note.type === 'video' && (
              <div className="absolute top-2 right-2 px-2 py-1 bg-black/60 rounded text-xs text-white">
                视频
              </div>
            )}
          </div>

          {/* 内容 */}
          <div className="p-4 space-y-3">
            <h4 className="text-sm font-medium text-text-primary line-clamp-2">
              {note.title}
            </h4>

            {/* 作者 */}
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-slate-200 overflow-hidden">
                {note.author.avatar && (
                  <img
                    src={note.author.avatar}
                    alt={note.author.nickname}
                    className="w-full h-full object-cover"
                  />
                )}
              </div>
              <span className="text-xs text-text-secondary truncate">
                {note.author.nickname}
              </span>
            </div>

            {/* 统计 */}
            <div className="flex items-center gap-4 text-xs text-text-secondary">
              <span className="flex items-center gap-1">
                <Heart className="w-3.5 h-3.5" />
                {formatNumber(note.like_count)}
              </span>
              <span className="flex items-center gap-1">
                <MessageCircle className="w-3.5 h-3.5" />
                {formatNumber(note.comment_count)}
              </span>
              <span className="flex items-center gap-1">
                <Bookmark className="w-3.5 h-3.5" />
                {formatNumber(note.collect_count)}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// 根据 ID 生成随机颜色
function getRandomColor(id: string): string {
  const colors = [
    '#F1F5F9', '#E0E7FF', '#FEF3C7', '#FCE7F3', '#D1FAE5', '#FEE2E2',
  ];
  const index = id.charCodeAt(0) % colors.length;
  return colors[index];
}
