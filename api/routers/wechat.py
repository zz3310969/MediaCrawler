import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from tools import utils

router = APIRouter(prefix="/wechat", tags=["wechat"])

class WeChatSearchRequest(BaseModel):
    keyword: str
    cookies: str
    token: str
    begin: int = 0
    count: int = 5

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

