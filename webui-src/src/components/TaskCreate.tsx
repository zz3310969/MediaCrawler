/**
 * 创建任务弹窗组件
 */
import React, { useState } from 'react';
import { tasksApi } from '../api/tasks';
import { 
  TaskCreateRequest, 
  Platform, 
  CrawlerType,
  TaskPriority,
  PlatformConfig,
  CrawlerTypeConfig 
} from '../types/task';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Switch } from './ui/switch';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from './ui/dialog';
import { Select } from './ui/select';

interface TaskCreateProps {
  open: boolean;
  onClose: () => void;
  onCreated: (taskId: string) => void;
}

interface FormState {
  task_name: string;
  platform: Platform;
  crawler_type: CrawlerType;
  keywords: string;           // 逗号分隔的关键词
  creator_ids: string;        // 逗号分隔的创作者ID/URL
  note_urls: string;          // 逗号分隔的笔记URL
  max_notes: number;
  enable_comments: boolean;
  max_comments_per_note: number;
  enable_media: boolean;
  concurrency: number;
  crawl_interval: number;
  cookies: string;            // Cookie 字符串
  save_option: 'csv' | 'json' | 'excel' | 'db' | 'sqlite';
  priority: number;
}

const initialFormState: FormState = {
  task_name: '',
  platform: 'xhs',
  crawler_type: 'search',
  keywords: '',
  creator_ids: '',
  note_urls: '',
  max_notes: 100,
  enable_comments: false,
  max_comments_per_note: 20,
  enable_media: false,
  concurrency: 3,
  crawl_interval: 1.0,
  cookies: '',
  save_option: 'json',
  priority: TaskPriority.NORMAL,
};

export const TaskCreate: React.FC<TaskCreateProps> = ({ 
  open, 
  onClose, 
  onCreated 
}) => {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState<FormState>(initialFormState);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // 验证
    if (form.crawler_type === 'search' && !form.keywords.trim()) {
      alert('请输入关键词');
      return;
    }
    if ((form.crawler_type === 'creator' || form.crawler_type === 'creator_vip') && !form.creator_ids.trim()) {
      alert('请输入创作者ID或主页URL');
      return;
    }
    if (form.crawler_type === 'detail' && !form.note_urls.trim()) {
      alert('请输入笔记/视频URL');
      return;
    }

    setLoading(true);

    try {
      // 将逗号分隔的字符串转为数组
      const parseList = (str: string) => 
        str.split(/[,，\n]/).map(s => s.trim()).filter(s => s.length > 0);

      const request: TaskCreateRequest = {
        task_name: form.task_name || undefined,
        config: {
          platform: form.platform,
          crawler_type: form.crawler_type,
          keywords: form.keywords ? parseList(form.keywords) : undefined,
          creator_ids: form.creator_ids ? parseList(form.creator_ids) : undefined,
          note_urls: form.note_urls ? parseList(form.note_urls) : undefined,
          max_notes: form.max_notes,
          enable_comments: form.enable_comments,
          max_comments_per_note: form.max_comments_per_note,
          enable_media: form.enable_media,
          concurrency: form.concurrency,
          crawl_interval: form.crawl_interval,
          cookies: form.cookies || undefined,
          save_option: form.save_option,
        },
        priority: form.priority,
      };

      const task = await tasksApi.create(request);
      onCreated(task.task_id);
      handleClose();
    } catch (error) {
      const err = error as Error;
      alert('创建失败: ' + (err.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setForm(initialFormState);
    setShowAdvanced(false);
    onClose();
  };

  const updateForm = (key: keyof FormState, value: FormState[keyof FormState]) => {
    setForm(prev => ({ ...prev, [key]: value }));
  };

  return (
    <Dialog open={open} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>创建新任务</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 任务名称 */}
          <div className="space-y-2">
            <Label htmlFor="task_name">任务名称（可选）</Label>
            <Input
              id="task_name"
              value={form.task_name}
              onChange={(e) => updateForm('task_name', e.target.value)}
              placeholder="例如: 小红书搜索-护肤品"
            />
          </div>

          {/* 平台选择 */}
          <div className="space-y-2">
            <Label>选择平台</Label>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(PlatformConfig) as Platform[]).map((p) => (
                <Button
                  key={p}
                  type="button"
                  variant={form.platform === p ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => updateForm('platform', p)}
                >
                  {PlatformConfig[p].label}
                </Button>
              ))}
            </div>
          </div>

          {/* 爬取类型 */}
          <div className="space-y-2">
            <Label>爬取类型</Label>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(CrawlerTypeConfig) as CrawlerType[]).map((t) => (
                <Button
                  key={t}
                  type="button"
                  variant={form.crawler_type === t ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => updateForm('crawler_type', t)}
                >
                  {CrawlerTypeConfig[t].label}
                </Button>
              ))}
            </div>
          </div>

          {/* 关键词（搜索模式） */}
          {form.crawler_type === 'search' && (
            <div className="space-y-2">
              <Label htmlFor="keywords">搜索关键词 *</Label>
              <textarea
                id="keywords"
                value={form.keywords}
                onChange={(e) => updateForm('keywords', e.target.value)}
                placeholder="多个关键词用逗号或换行分隔，例如：&#10;护肤品,美妆&#10;穿搭"
                className="w-full min-h-[80px] px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-800 dark:border-slate-700"
                required
              />
            </div>
          )}

          {/* 创作者ID/URL（创作者模式） */}
          {(form.crawler_type === 'creator' || form.crawler_type === 'creator_vip') && (
            <div className="space-y-2">
              <Label htmlFor="creator_ids">创作者主页URL *</Label>
              <textarea
                id="creator_ids"
                value={form.creator_ids}
                onChange={(e) => updateForm('creator_ids', e.target.value)}
                placeholder="输入创作者主页URL，多个用逗号或换行分隔，例如：&#10;https://www.xiaohongshu.com/user/profile/xxx"
                className="w-full min-h-[80px] px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-800 dark:border-slate-700"
                required
              />
            </div>
          )}

          {/* 笔记URL（详情模式） */}
          {form.crawler_type === 'detail' && (
            <div className="space-y-2">
              <Label htmlFor="note_urls">笔记/视频URL *</Label>
              <textarea
                id="note_urls"
                value={form.note_urls}
                onChange={(e) => updateForm('note_urls', e.target.value)}
                placeholder="输入笔记/视频URL，多个用逗号或换行分隔，例如：&#10;https://www.xiaohongshu.com/explore/xxx"
                className="w-full min-h-[80px] px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-800 dark:border-slate-700"
                required
              />
            </div>
          )}

          {/* 高级选项 */}
          <div className="border rounded-lg p-4 space-y-4">
            <button
              type="button"
              className="flex items-center justify-between w-full text-left"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              <span className="font-medium">高级选项</span>
              <span>{showAdvanced ? '收起 ▲' : '展开 ▼'}</span>
            </button>

            {showAdvanced && (
              <div className="space-y-4 pt-2">
                {/* 数量配置 */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="max_notes">最大爬取数</Label>
                    <Input
                      id="max_notes"
                      type="number"
                      value={form.max_notes}
                      onChange={(e) => updateForm('max_notes', parseInt(e.target.value) || 100)}
                      min={1}
                      max={1000}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="priority">优先级</Label>
                    <Select
                      value={String(form.priority)}
                      onChange={(e) => updateForm('priority', parseInt(e.target.value))}
                    >
                      <option value={String(TaskPriority.LOW)}>低</option>
                      <option value={String(TaskPriority.NORMAL)}>普通</option>
                      <option value={String(TaskPriority.HIGH)}>高</option>
                      <option value={String(TaskPriority.URGENT)}>紧急</option>
                    </Select>
                  </div>
                </div>

                {/* 执行配置 */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="concurrency">并发数</Label>
                    <Input
                      id="concurrency"
                      type="number"
                      value={form.concurrency}
                      onChange={(e) => updateForm('concurrency', parseInt(e.target.value) || 3)}
                      min={1}
                      max={10}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="crawl_interval">请求间隔(秒)</Label>
                    <Input
                      id="crawl_interval"
                      type="number"
                      step="0.1"
                      value={form.crawl_interval}
                      onChange={(e) => updateForm('crawl_interval', parseFloat(e.target.value) || 1.0)}
                      min={0.1}
                      max={10}
                    />
                  </div>
                </div>

                {/* 保存格式 */}
                <div className="space-y-2">
                  <Label htmlFor="save_option">保存格式</Label>
                  <Select
                    value={form.save_option}
                    onChange={(e) => updateForm('save_option', e.target.value as FormState['save_option'])}
                  >
                    <option value="json">JSON 文件</option>
                    <option value="csv">CSV 文件</option>
                    <option value="excel">Excel 文件</option>
                    <option value="sqlite">SQLite 数据库</option>
                    <option value="db">MySQL 数据库</option>
                  </Select>
                </div>

                {/* 功能开关 */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="enable_comments">爬取评论</Label>
                    <Switch
                      id="enable_comments"
                      checked={form.enable_comments}
                      onCheckedChange={(checked) => updateForm('enable_comments', checked)}
                    />
                  </div>

                  {form.enable_comments && (
                    <div className="space-y-2 ml-4">
                      <Label htmlFor="max_comments_per_note">每条笔记最大评论数</Label>
                      <Input
                        id="max_comments_per_note"
                        type="number"
                        value={form.max_comments_per_note}
                        onChange={(e) => updateForm('max_comments_per_note', parseInt(e.target.value) || 20)}
                        min={1}
                        max={100}
                      />
                    </div>
                  )}

                  <div className="flex items-center justify-between">
                    <Label htmlFor="enable_media">下载图片/视频</Label>
                    <Switch
                      id="enable_media"
                      checked={form.enable_media}
                      onCheckedChange={(checked) => updateForm('enable_media', checked)}
                    />
                  </div>
                </div>

                {/* Cookie 配置 */}
                <div className="space-y-2 border-t pt-4 mt-4">
                  <Label htmlFor="cookies">
                    Cookie（可选）
                    <span className="text-xs text-gray-500 ml-2">
                      如果没有保存的登录状态，请填写 Cookie
                    </span>
                  </Label>
                  <textarea
                    id="cookies"
                    value={form.cookies}
                    onChange={(e) => updateForm('cookies', e.target.value)}
                    placeholder="从浏览器开发者工具复制 Cookie 字符串粘贴到这里...&#10;&#10;获取方法：浏览器 F12 → Network → 任意请求 → Headers → Cookie"
                    className="w-full min-h-[100px] px-3 py-2 text-xs font-mono border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-800 dark:border-slate-700"
                  />
                  <p className="text-xs text-amber-600 dark:text-amber-400">
                    ⚠️ 首次使用建议先运行命令行版本完成扫码登录：<code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">uv run main.py --platform {form.platform} --lt qrcode</code>
                  </p>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>
              取消
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? '创建中...' : '创建任务'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default TaskCreate;
