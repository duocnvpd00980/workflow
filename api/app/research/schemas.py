from pydantic import BaseModel, Field, field_validator, model_validator
from urllib.parse import urlparse
from fastapi import HTTPException
import httpx
import re


class TestPipelineRequest(BaseModel):
    query: str = Field(..., description="Query nghiên cứu")

    fb_url: str = Field(
        default="popup_only.html",
        description="Path file HTML Facebook",
    )

    business_id: str | None = None

    business_name: str | None = None


    @field_validator("query")
    @classmethod
    def clean_query(cls, v: str):

        v = v.strip()

        if not v:
            raise ValueError(
                "query không được rỗng"
            )

        return v


    @field_validator("fb_url")
    @classmethod
    def clean_fb_url(cls, raw: str):

        if raw == "popup_only.html":
            return raw

        raw = raw.strip()

        # bỏ ký tự copy dư
        raw = raw.strip(
            "\"'`()[]{}<> "
        )

        # extract URL
        m = re.search(
            r"(https?:\/\/[^\s]+|(?:www\.)?facebook\.com\/[^\s]+)",
            raw,
            re.I,
        )

        if m:
            raw = m.group(0)

        # thêm protocol
        if raw.startswith("facebook.com"):
            raw = "https://" + raw

        if raw.startswith("www.facebook.com"):
            raw = "https://" + raw

        parsed = urlparse(raw)

        if not parsed.netloc:
            raise ValueError(
                "Facebook URL không hợp lệ"
            )

        if "facebook.com" not in parsed.netloc.lower():
            raise ValueError(
                "Chỉ hỗ trợ URL Facebook"
            )

        path = parsed.path.strip("/")

        if not path:
            raise ValueError(
                "Thiếu đường dẫn Facebook"
            )

        return (
            f"https://www.facebook.com/{path}"
        )


    @model_validator(mode="after")
    def clean_business_name(self):

        if not self.business_name:
            self.business_name = (
                self.query[:50]
            )

        self.business_name = (
            self.business_name
            .strip()
        )

        return self


    async def validate_fb_exists(self):

        if self.fb_url.endswith(".html"):
            return

        try:

            async with httpx.AsyncClient(
                timeout=10,
                follow_redirects=True,
                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                },
            ) as client:

                r = await client.get(
                    self.fb_url
                )

                html = r.text.lower()

                if (
                    r.status_code >= 400
                ):
                    raise HTTPException(
                        404,
                        (
                            "Facebook URL "
                            "không tồn tại"
                        ),
                    )

                invalid = [
                    "content isn't available",
                    "page isn't available",
                    "the link you followed",
                    "not found",
                    "trang này hiện không khả dụng",
                ]

                if any(
                    x in html
                    for x in invalid
                ):
                    raise HTTPException(
                        404,
                        (
                            "Facebook "
                            "không tồn tại "
                            "hoặc bị xoá"
                        ),
                    )

        except httpx.TimeoutException:

            raise HTTPException(
                408,
                "Timeout kiểm tra Facebook",
            )

        except httpx.RequestError:

            raise HTTPException(
                400,
                "Không thể kết nối Facebook",
            )