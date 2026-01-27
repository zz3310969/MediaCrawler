import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from tools import utils

router = APIRouter(prefix="/wechat", tags=["wechat"])


# ==================== 请求/响应模型 ====================

class WeChatSearchRequest(BaseModel):
    keyword: str
    cookies: str
    token: str
    begin: int = 0
    count: int = 5


class ArticleItem(BaseModel):
    """文章列表项"""
    id: int
    article_id: str
    title: str
    account_name: str
    read_num: int
    like_num: int
    comment_count: int
    create_time: int
    link: str
    cover: Optional[str] = None


class ArticleListResponse(BaseModel):
    """文章列表响应"""
    articles: List[ArticleItem]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    """统计数据响应"""
    total_articles: int
    total_reads: int
    total_likes: int
    total_accounts: int
    today_articles: int
    today_reads: int


class TopArticleItem(BaseModel):
    """热门文章项"""
    id: int
    title: str
    account_name: str
    read_num: int
    create_time: int


class AccountItem(BaseModel):
    """公众号列表项"""
    fakeid: str
    account_name: str
    article_count: int


@router.get("/accounts", response_model=List[AccountItem])
async def get_accounts():
    """
    获取所有已采集的公众号列表（去重）
    """
    try:
        from database.db_session import get_session
        from database.models import WeChatArticle
        from sqlalchemy import select, func, distinct
        
        async with get_session() as session:
            # 获取所有公众号及其文章数量
            query = select(
                WeChatArticle.fakeid,
                WeChatArticle.account_name,
                func.count(WeChatArticle.id).label('article_count')
            ).group_by(
                WeChatArticle.fakeid,
                WeChatArticle.account_name
            ).order_by(
                func.count(WeChatArticle.id).desc()
            )
            
            result = await session.execute(query)
            accounts = result.all()
            
            return [
                AccountItem(
                    fakeid=row.fakeid or "",
                    account_name=row.account_name or "未知公众号",
                    article_count=row.article_count or 0,
                )
                for row in accounts
                if row.fakeid  # 过滤掉空的 fakeid
            ]
            
    except Exception as e:
        utils.logger.error(f"[WeChatAPI] Get accounts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search_account")
async def search_account(request: WeChatSearchRequest):
    """
    搜索公众号
    """
    if not request.token:
        raise HTTPException(status_code=400, detail="Token is required")

    uri = "https://mp.weixin.qq.com/cgi-bin/searchbiz"
    params = {
        "action": "search_biz",
        "begin": request.begin,
        "count": request.count,
        "query": request.keyword,
        "token": request.token,
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": request.cookies,
        "Referer": f"https://mp.weixin.qq.com/cgi-bin/home?t=home/index&token={request.token}&lang=zh_CN"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(uri, params=params, headers=headers)
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="HTTP error from WeChat")

            try:
                data = response.json()
            except Exception:
                 raise HTTPException(status_code=500, detail="Invalid JSON response from WeChat")
            
            # Check for errors
            base_resp = data.get("base_resp", {})
            ret = base_resp.get("ret")
            if ret != 0:
                err_msg = base_resp.get("err_msg", "Unknown error")
                if ret == 200003:
                    raise HTTPException(status_code=429, detail="Rate limited (freq control)")
                if ret == 200013:
                     raise HTTPException(status_code=401, detail="Session expired")
                raise HTTPException(status_code=400, detail=f"WeChat API error ({ret}): {err_msg}")
                
            return data
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"[WeChatAPI] Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 数据查询 API ====================

@router.get("/articles", response_model=ArticleListResponse)
async def get_articles(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索标题"),
    time_range: Optional[str] = Query(None, description="时间范围: today, week, month, all"),
    order_by: Optional[str] = Query("create_time", description="排序字段: create_time, read_num, like_num"),
    order_dir: Optional[str] = Query("desc", description="排序方向: asc, desc"),
    account_ids: Optional[str] = Query(None, description="公众号ID列表，逗号分隔"),
):
    """
    获取微信文章列表（分页）
    """
    try:
        from database.db_session import get_session
        from database.models import WeChatArticle
        from sqlalchemy import select, func, desc, asc
        
        async with get_session() as session:
            # 构建基础查询
            query = select(WeChatArticle)
            count_query = select(func.count(WeChatArticle.id))
            
            # 公众号过滤
            if account_ids:
                fakeid_list = [fid.strip() for fid in account_ids.split(",") if fid.strip()]
                if fakeid_list:
                    account_filter = WeChatArticle.fakeid.in_(fakeid_list)
                    query = query.where(account_filter)
                    count_query = count_query.where(account_filter)
            
            # 搜索条件
            if search:
                search_filter = WeChatArticle.title.ilike(f"%{search}%")
                query = query.where(search_filter)
                count_query = count_query.where(search_filter)
            
            # 时间范围过滤
            if time_range and time_range != "all":
                now = datetime.now()
                if time_range == "today":
                    start_ts = int(datetime(now.year, now.month, now.day).timestamp())
                elif time_range == "week":
                    start_ts = int((now - timedelta(days=7)).timestamp())
                elif time_range == "month":
                    start_ts = int((now - timedelta(days=30)).timestamp())
                else:
                    start_ts = None
                
                if start_ts:
                    time_filter = WeChatArticle.create_time >= start_ts
                    query = query.where(time_filter)
                    count_query = count_query.where(time_filter)
            
            # 排序
            order_column = getattr(WeChatArticle, order_by, WeChatArticle.create_time)
            if order_dir == "asc":
                query = query.order_by(asc(order_column))
            else:
                query = query.order_by(desc(order_column))
            
            # 获取总数
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0
            
            # 分页
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            # 执行查询
            result = await session.execute(query)
            articles = result.scalars().all()
            
            # 转换为响应格式
            article_list = [
                ArticleItem(
                    id=article.id,
                    article_id=article.article_id,
                    title=article.title or "",
                    account_name=article.account_name or "",
                    read_num=article.read_num or 0,
                    like_num=article.like_num or 0,
                    comment_count=article.comment_count or 0,
                    create_time=article.create_time or 0,
                    link=article.link or "",
                    cover=article.cover,
                )
                for article in articles
            ]
            
            return ArticleListResponse(
                articles=article_list,
                total=total,
                page=page,
                page_size=page_size,
            )
            
    except Exception as e:
        utils.logger.error(f"[WeChatAPI] Get articles failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    获取微信数据统计
    """
    try:
        from database.db_session import get_session
        from database.models import WeChatArticle
        from sqlalchemy import select, func, distinct
        
        async with get_session() as session:
            # 文章总数
            total_articles_result = await session.execute(
                select(func.count(WeChatArticle.id))
            )
            total_articles = total_articles_result.scalar() or 0
            
            # 总阅读量
            total_reads_result = await session.execute(
                select(func.sum(WeChatArticle.read_num))
            )
            total_reads = total_reads_result.scalar() or 0
            
            # 总点赞数
            total_likes_result = await session.execute(
                select(func.sum(WeChatArticle.like_num))
            )
            total_likes = total_likes_result.scalar() or 0
            
            # 公众号数量（去重）
            total_accounts_result = await session.execute(
                select(func.count(distinct(WeChatArticle.fakeid)))
            )
            total_accounts = total_accounts_result.scalar() or 0
            
            # 今日新增文章数
            today = datetime.now()
            today_start = int(datetime(today.year, today.month, today.day).timestamp())
            today_articles_result = await session.execute(
                select(func.count(WeChatArticle.id)).where(
                    WeChatArticle.add_ts >= today_start * 1000  # add_ts 是毫秒
                )
            )
            today_articles = today_articles_result.scalar() or 0
            
            # 今日新增阅读量
            today_reads_result = await session.execute(
                select(func.sum(WeChatArticle.read_num)).where(
                    WeChatArticle.add_ts >= today_start * 1000
                )
            )
            today_reads = today_reads_result.scalar() or 0
            
            return StatsResponse(
                total_articles=total_articles,
                total_reads=int(total_reads),
                total_likes=int(total_likes),
                total_accounts=total_accounts,
                today_articles=today_articles,
                today_reads=int(today_reads) if today_reads else 0,
            )
            
    except Exception as e:
        utils.logger.error(f"[WeChatAPI] Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top_articles", response_model=List[TopArticleItem])
async def get_top_articles(
    limit: int = Query(5, ge=1, le=20, description="返回数量"),
):
    """
    获取热门文章 Top N（按阅读量排序）
    """
    try:
        from database.db_session import get_session
        from database.models import WeChatArticle
        from sqlalchemy import select, desc
        
        async with get_session() as session:
            query = select(WeChatArticle).order_by(desc(WeChatArticle.read_num)).limit(limit)
            result = await session.execute(query)
            articles = result.scalars().all()
            
            return [
                TopArticleItem(
                    id=article.id,
                    title=article.title or "",
                    account_name=article.account_name or "",
                    read_num=article.read_num or 0,
                    create_time=article.create_time or 0,
                )
                for article in articles
            ]
            
    except Exception as e:
        utils.logger.error(f"[WeChatAPI] Get top articles failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

