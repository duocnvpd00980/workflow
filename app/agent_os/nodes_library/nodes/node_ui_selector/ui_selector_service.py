import json
from typing import List, Dict, Any
from pydantic import ValidationError

# Import chính xác toàn bộ hệ thống schema bạn đã định nghĩa
from .ui_selector_protocol import (
    ComponentSelection,
    LLMSelectorResponse,
    UISelectorOutput,
    RenderedComponent,
    COMPONENT_REGISTRY,
    PROPS_SCHEMA_MAP,
    ComponentId,
)
from agent_os.system.bus.protocol import BodyFrame


class UISelectorService:
    """
    UI SELECTOR DOMAIN SERVICE (PURE LOGIC)
    Nhiệm vụ: Nhận Object BodyFrame phẳng từ Finalizer, phân tích dữ liệu thực tế
    để ánh xạ và ÉP KIỂU chặt chẽ qua Pydantic Props Schema trước khi render.
    """

    def select_components(self, finalizer_payload: BodyFrame) -> LLMSelectorResponse:
        """
        Bước 1: Phân tích cấu trúc dữ liệu phẳng của Bus để quyết định danh sách ComponentId cần hiển thị.
        """
        selections: List[ComponentSelection] = []

        # 1. TRƯỜNG HỢP PIPELINE BÁO LỖI (ERROR FIRST)
        if finalizer_payload.status == "FAILED":
            selections.append(
                ComponentSelection(
                    component_id="error_card",
                    props={},
                    reason=f"Pipeline failure detected: {finalizer_payload.error}",
                )
            )
            return LLMSelectorResponse(selections=selections)

        # Lấy an toàn dữ liệu từ state và text
        state_data = finalizer_payload.state or {}
        flow_type = state_data.get("flow_type", "default")
        records = finalizer_payload.records or []
        text_content = finalizer_payload.text or ""

        # --- TỪ KHÓA ĐẶC TRƯNG CỦA TRẠNG THÁI TRỐNG (AI PHẢN HỒI) ---
        empty_keywords = [
            "chưa tìm thấy",
            "không tìm thấy",
            "không có dữ liệu",
            "không phù hợp",
            "xin lỗi",
        ]
        is_text_empty_signal = any(kw in text_content.lower() for kw in empty_keywords)

        # 2. TRƯỜNG HỢP KHÔNG CÓ DỮ LIỆU (EMPTY STATE - PHÒNG VỆ THÔNG MINH)
        # Bắt THÊM cả trường hợp records trống kèm text chứa tín hiệu không tìm thấy kết quả
        if (not text_content and not records) or (not records and is_text_empty_signal):
            selections.append(
                ComponentSelection(
                    component_id="empty_state",
                    props={},
                    reason=f"Empty state triggered by text signal or zero records. Text: '{text_content}'",
                )
            )
            return LLMSelectorResponse(selections=selections)

        # 3. PHÂN TÍCH DATA THỰC TẾ TRONG RECORDS ĐỂ ĐỊNH TUYẾN COMPONENT (DATA-DRIVEN)
        has_ads = any(isinstance(r, dict) and "headline" in r for r in records)
        has_email = any(isinstance(r, dict) and "subject" in r for r in records)
        has_blog = any(isinstance(r, dict) and "title" in r for r in records)

        # Chiến dịch tổng hợp (đầy đủ các thành phần)
        if has_ads and has_email and has_blog:
            selections.append(
                ComponentSelection(component_id="campaign_summary", props={})
            )
            selections.append(ComponentSelection(component_id="ads_card", props={}))
            selections.append(
                ComponentSelection(component_id="email_template", props={})
            )
            selections.append(ComponentSelection(component_id="blog_preview", props={}))
            return LLMSelectorResponse(selections=selections)

        # Định tuyến dựa trên cấu trúc bản ghi thực tế
        if has_ads:
            selections.append(ComponentSelection(component_id="ads_card", props={}))
        elif has_email:
            selections.append(
                ComponentSelection(component_id="email_template", props={})
            )
        elif has_blog:
            selections.append(ComponentSelection(component_id="blog_preview", props={}))

        # 4. ĐỊNH TUYẾN DỰ PHÒNG DỰA TRÊN FLOW_TYPE CỦA STATE (NẾU RECORDS KHÔNG CHỨA KHÓA ĐẶC TRƯNG)
        if not selections:
            if flow_type in ["ads_only", "marketing"] and text_content:
                # Nếu tầng trên báo là luồng marketing/ads nhưng trả về text chuỗi dài -> map tạm vào ads_card/blog_preview
                selections.append(ComponentSelection(component_id="ads_card", props={}))
            elif flow_type == "qa" or flow_type == "chat":
                selections.append(
                    ComponentSelection(component_id="text_response", props={})
                )

        # Hạ cánh an toàn cuối cùng
        if not selections:
            selections.append(
                ComponentSelection(component_id="text_response", props={})
            )

        return LLMSelectorResponse(selections=selections)

    def resolve_ui(
        self, selector_res: LLMSelectorResponse, finalizer_payload: BodyFrame
    ) -> UISelectorOutput:
        """
        Bước 2: Gom dữ liệu thô, nạp default values và THỰC HIỆN VALIDATE NGHIÊM NGẶT qua Props Schema.
        """
        rendered_list: List[RenderedComponent] = []
        fallback_used = False
        status = "success"

        records = finalizer_payload.records or []
        state_data = finalizer_payload.state or {}
        context_data = finalizer_payload.context or {}

        # Trích xuất nhanh các bản ghi thô từ thượng nguồn gửi về (nếu có)
        raw_ads = next(
            (r for r in records if isinstance(r, dict) and "headline" in r), {}
        )
        raw_email = next(
            (r for r in records if isinstance(r, dict) and "subject" in r), {}
        )
        raw_blog = next(
            (r for r in records if isinstance(r, dict) and "title" in r), {}
        )

        for selection in selector_res.selections:
            cid: ComponentId = selection.component_id
            raw_props: Dict[str, Any] = {}

            # --- MAP DỮ LIỆU THÔ VÀO TỪNG COMPONENT KHỚP VỚI REQUIRED_PROPS ---
            if cid == "error_card":
                raw_props = {
                    "message": finalizer_payload.text
                    or "Hệ thống trục trặc, vui lòng thử lại.",
                    "title": "Sự cố xử lý dữ liệu",
                    "error_code": finalizer_payload.error or "PIPELINE_ERROR",
                    "failed_node": context_data.get("failed_node", "node_FINALIZER"),
                    "debug_details": context_data.get("exception_trace")
                    or finalizer_payload.error,
                }
            elif cid == "empty_state":
                raw_props = {
                    "title": "Không tìm thấy nội dung kết quả",
                    "description": finalizer_payload.text
                    or "Hệ thống đã chạy hoàn tất nhưng không trích xuất được dữ liệu phù hợp.",
                    "user_input": context_data.get("user_prompt"),
                }
            elif cid == "text_response":
                raw_props = {
                    "text": finalizer_payload.text or "No text content returned.",
                    "title": "Kết quả xử lý",
                }
            elif cid == "ads_card":
                raw_props = (
                    raw_ads
                    if raw_ads
                    else {
                        "headline": "Chiến dịch quảng cáo",
                        "body": finalizer_payload.text or "",
                    }
                )
            elif cid == "email_template":
                raw_props = (
                    raw_email
                    if raw_email
                    else {
                        "subject": "Thông tin gửi tới bạn",
                        "body": finalizer_payload.text or "",
                    }
                )
            elif cid == "blog_preview":
                raw_props = (
                    raw_blog
                    if raw_blog
                    else {
                        "title": "Bài viết mới cập nhật",
                        "content": finalizer_payload.text or "",
                    }
                )
            elif cid == "campaign_summary":
                # Đếm tổng số lượng chữ tổng quan của toàn bộ chiến dịch dữ liệu phẳng
                ready_list = []
                if raw_ads:
                    ready_list.append("ads_card")
                if raw_email:
                    ready_list.append("email_template")
                if raw_blog:
                    ready_list.append("blog_preview")

                raw_props = {
                    "status": "completed"
                    if finalizer_payload.status == "SUCCESS"
                    else "pending",
                    "components_ready": ready_list,
                    "message": "Toàn bộ tài nguyên chiến dịch marketing đã được tạo lập thành công phẳng sạch.",
                    "total_words": len(finalizer_payload.text or ""),
                }

            # --- QUY TRÌNH ÉP KIỂU VÀ VALIDATE CHẶT CHẼ QUA SCHEMAS MAP ---
            try:
                schema_model = PROPS_SCHEMA_MAP.get(cid)
                if not schema_model:
                    raise ValueError(
                        f"Missing schema model class mapping for component_id: {cid}"
                    )

                # Ép kiểu thông qua Pydantic thực thụ -> Tự điền default_factory, loại bỏ trường thừa Extra="ignore"
                validated_props_obj = schema_model.model_validate(raw_props)
                validated_props = validated_props_obj.model_dump()

                registry_config = COMPONENT_REGISTRY.get(cid, {})
                template_path = registry_config.get(
                    "template_path", f"widgets/{cid}.html"
                )

                rendered_list.append(
                    RenderedComponent(
                        component_id=cid,
                        props=validated_props,
                        template_path=template_path,
                    )
                )

            except (ValidationError, Exception) as val_err:
                # SAFE FALLBACK CRASH PROTECTION: Nếu bất kỳ component nghiệp vụ nào lỗi cấu trúc,
                # lập tức cứu hộ bằng cách kích hoạt Text Response chứa Plain Text an toàn để cứu giao diện
                print(
                    f"⚠️ [UI_SELECTOR_SERVICE] Schema Validation Failed for '{cid}': {str(val_err)}"
                )
                fallback_used = True
                status = "fallback"

                # Bơm khẩn cấp text_response cứu hộ
                rendered_list.append(
                    RenderedComponent(
                        component_id="text_response",
                        props={
                            "text": finalizer_payload.text
                            or "Hệ thống lỗi sinh cấu trúc giao diện hiển thị phức tạp.",
                            "title": "Phản hồi dự phòng hệ thống",
                        },
                        template_path=COMPONENT_REGISTRY["text_response"][
                            "template_path"
                        ],
                    )
                )

        return UISelectorOutput(
            rendered_components=rendered_list,
            fallback_used=fallback_used,
            selector_status=status,
            raw_text_fallback=finalizer_payload.text if fallback_used else None,
        )
