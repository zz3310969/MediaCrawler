import { WechatArticle } from '../../types';
import { formatRelativeTime, formatNumber } from '../../lib/utils';

interface WechatArticleListProps {
  articles: WechatArticle[];
  selectedIds: string[];
  onSelectChange: (ids: string[]) => void;
}

export function WechatArticleList({ articles, selectedIds, onSelectChange }: WechatArticleListProps) {
  const handleSelectAll = () => {
    if (selectedIds.length === articles.length) {
      onSelectChange([]);
    } else {
      onSelectChange(articles.map((a) => a.id));
    }
  };

  const handleSelect = (id: string) => {
    if (selectedIds.includes(id)) {
      onSelectChange(selectedIds.filter((i) => i !== id));
    } else {
      onSelectChange([...selectedIds, id]);
    }
  };

  return (
    <div className="space-y-0">
      {/* 全选行 */}
      <div className="flex items-center gap-3 py-3 border-b border-border">
        <input
          type="checkbox"
          checked={selectedIds.length === articles.length && articles.length > 0}
          onChange={handleSelectAll}
          className="w-[18px] h-[18px] rounded border-slate-300"
        />
        <span className="text-sm text-text-secondary">全选当前页</span>
      </div>

      {/* 文章列表 */}
      {articles.map((article) => (
        <div
          key={article.id}
          className="flex gap-4 py-4 border-b border-slate-100 last:border-b-0"
        >
          {/* 复选框 */}
          <input
            type="checkbox"
            checked={selectedIds.includes(article.id)}
            onChange={() => handleSelect(article.id)}
            className="w-[18px] h-[18px] rounded border-slate-300 flex-shrink-0 mt-1"
          />

          {/* 封面图 */}
          {article.cover && (
            <div className="w-[100px] h-[75px] rounded-lg bg-slate-200 overflow-hidden flex-shrink-0">
              <img
                src={article.cover}
                alt={article.title}
                className="w-full h-full object-cover"
              />
            </div>
          )}

          {/* 内容 */}
          <div className="flex-1 min-w-0 space-y-2">
            <h4 className="text-sm font-medium text-text-primary line-clamp-2">
              {article.title}
            </h4>
            <p className="text-xs text-text-secondary line-clamp-2">
              {article.digest}
            </p>
            <div className="flex items-center gap-4 text-xs text-text-secondary">
              <span className="flex items-center gap-1">
                <span className="w-5 h-5 rounded-full bg-slate-100" />
                {article.author.name}
              </span>
              <span>阅读 {formatNumber(article.read_count)}</span>
              <span>点赞 {formatNumber(article.like_count)}</span>
              <span>{formatRelativeTime(article.published_at)}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
