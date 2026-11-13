# Đối chiếu API và quyền truy cập

[Tài liệu chung](README.md) · [Phạm vi MVP](mvp.md)

Ảnh chụp ngày 05/11/2026. Các bảng tóm tắt hành vi để nhóm phối hợp. Backend sở hữu hợp đồng HTTP và chính sách truy cập. Nguồn đối chiếu là OpenAPI, mã endpoint, use case và kiểm thử tại cùng mốc. [OpenAPI backend](https://github.com/supportflow-ai/ai-it-service-desk/blob/bf38ef903f46f6ea21f80da44c11d437391a9efb/contracts/backend/openapi-baseline.json) · [Điểm vào Ticketing](https://github.com/supportflow-ai/ai-it-service-desk/blob/bf38ef903f46f6ea21f80da44c11d437391a9efb/src/backend/ServiceDesk.Api/Endpoints/TicketEndpoints.cs)

## API và quyền theo thao tác

Các đường dẫn trong bảng dùng tiền tố `/api`. Staff gồm Agent và Admin. Backend kết hợp vai trò với phạm vi dữ liệu, chủ sở hữu, trạng thái và revision. Web phản ánh các điều kiện để hiển thị thao tác.

| Phương thức và đường dẫn | Người gọi | Ràng buộc chính |
| --- | --- | --- |
| `POST /auth/register`, `POST /auth/login` | Khách hoặc người đã đăng nhập | Đăng ký `201`, đăng nhập `200`. Đăng ký cấp `Requester` |
| `GET /auth/me` | Đã xác thực | Lấy hồ sơ của chính người gọi |
| `GET /users?role=Agent` | Staff | Mặc định lọc Agent, có thể yêu cầu Admin. Phản hồi thực tế gồm `userId`, `fullName` |
| `POST /tickets`, `GET /tickets/me` | Requester, Agent, Admin | Tạo và liệt kê theo người gọi. Tạo `201` có `Location`. `Idempotency-Key` tùy chọn trên thao tác tạo |
| `GET /tickets/{id}` | Requester xem phiếu của mình, staff xem toàn hệ thống | Phiếu ngoài phạm vi đọc hoặc thiếu trả `404` |
| `GET /tickets/queue` | Staff | Phân trang và lọc theo tham số OpenAPI. Backend có `priority` và `sortByPriority` |
| `POST /tickets/{id}/update` | Chủ phiếu hoặc Admin | Chỉ khi `Submitted`. `expectedRevision` nằm trong body |
| `POST /tickets/{id}/assign` | Staff | Người nhận có vai trò Agent. `expectedRevision` nằm trong body |
| `POST /tickets/{id}/unassign` | Staff | Chỉ khi `Assigned` và có người nhận. `expectedRevision` nằm trong query |
| `POST /tickets/{id}/claim`, `POST /tickets/{id}/resolve` | Staff | Claim từ `Submitted` hoặc `Assigned`. Nếu đã phân cho Agent khác, Admin có ngoại lệ. Resolve từ `InProgress`. Revision nằm trong query |
| `POST /tickets/{id}/reopen`, `POST /tickets/{id}/close`, `POST /tickets/{id}/cancel` | Chủ phiếu hoặc Admin | Mở lại hoặc đóng từ `Resolved`, hủy từ `Submitted`. Revision nằm trong query |
| `POST /tickets/{id}/comments`, `POST /tickets/{id}/internal-notes`, `GET /tickets/{id}/timeline` | Bình luận và đọc theo quyền phiếu. Ghi chú chỉ cho staff | Backend lọc ghi chú nội bộ khi Requester đọc timeline |
| `POST /tickets/{id}/attachments/upload-url`, `POST /tickets/{id}/attachments/confirm` | Theo quyền phiếu và grant | Upload theo chỉ dẫn từ API. Grant gắn người gọi, phiếu và metadata. Backend kiểm tra object khi confirm |
| `GET /tickets/{id}/attachments`, `GET /tickets/{id}/attachments/download-url` | Theo quyền phiếu và tệp | Backend cấp URL tải xuống cho tệp đã có metadata hợp lệ |

Revision dương là điều kiện của các lệnh cập nhật, phân công và chuyển trạng thái ở backend hiện tại. Revision cũ trả `409`. Một số tham số và thuộc tính OpenAPI vẫn thể hiện tùy chọn. `TicketStatus` dùng số nguyên, trong đó phiếu mới là `Submitted (1)`. Phản hồi lỗi nghiệp vụ dùng `{ "error": "..." }` theo bộ lọc hiện hành. Đọc tài nguyên ngoài phạm vi thường nhận `404`. Tệp có key ngoài tiền tố của một phiếu đã đọc được trả `403`. [Bộ lọc lỗi](https://github.com/supportflow-ai/ai-it-service-desk/blob/bf38ef903f46f6ea21f80da44c11d437391a9efb/src/backend/ServiceDesk.Api/Endpoints/LegacyErrorFilter.cs) · [Quyền tải tệp](https://github.com/supportflow-ai/ai-it-service-desk/blob/bf38ef903f46f6ea21f80da44c11d437391a9efb/src/backend/ServiceDesk.Application/Ticketing/GetAttachmentDownloadUrl/GetAttachmentDownloadUrlUseCase.cs)

## Kiểm tra phối hợp trước demo

| Chủ đề | Bằng chứng tại các mốc đã ghim | Tác động và trạng thái |
| --- | --- | --- |
| Danh bạ Agent | Backend trả `userId` và `fullName`. Web đọc hai trường này, với `fullName` có thể rỗng | Thử phân công với danh bạ có kỹ thuật viên từ backend thật. [Backend](https://github.com/supportflow-ai/ai-it-service-desk/blob/bf38ef903f46f6ea21f80da44c11d437391a9efb/src/backend/ServiceDesk.Api/Endpoints/AuthEndpoints.cs) · [Web](https://github.com/supportflow-ai/ai-it-service-desk-web/blob/ade7af4e1b88e7834c8d9b225f68eb7ebd75f9fe/src/features/tickets/api/ticketContract.ts) |
| Nhận xử lý và hủy phân công | Web hiển thị nhận phiếu cho Agent và Admin theo trạng thái và người phụ trách. Web chỉ hiển thị hủy phân công ở trạng thái `Assigned` | Nghiệm thu quyền cho Agent được giao, Agent khác và Admin. [Backend](https://github.com/supportflow-ai/ai-it-service-desk/blob/bf38ef903f46f6ea21f80da44c11d437391a9efb/src/backend/ServiceDesk.Application/Ticketing/ClaimTicket/ClaimTicketUseCase.cs) · [Web](https://github.com/supportflow-ai/ai-it-service-desk-web/blob/ade7af4e1b88e7834c8d9b225f68eb7ebd75f9fe/src/features/tickets/model/ticketPermissions.ts) |
| Ưu tiên trong hàng đợi | Backend và Web hỗ trợ lọc và sắp xếp theo ưu tiên | Thử bộ lọc với các phiếu có mức ưu tiên khác nhau. [Web](https://github.com/supportflow-ai/ai-it-service-desk-web/blob/ade7af4e1b88e7834c8d9b225f68eb7ebd75f9fe/src/features/tickets/components/AgentQueueToolbar.tsx) |
| Snapshot OpenAPI của Web | Snapshot ghim Backend `dev@febb4d7` và khớp từng byte với OpenAPI của Backend `main@bf38ef9` | Khi phát hành chung, kiểm thêm với đúng bản Backend dùng để chạy demo. [Nguồn snapshot](https://github.com/supportflow-ai/ai-it-service-desk-web/blob/ade7af4e1b88e7834c8d9b225f68eb7ebd75f9fe/tests/contracts/backend-source.json) |
| Hợp đồng revision | Use case bắt buộc revision dương ở các lệnh trên. Một số khai báo trong OpenAPI còn cho phép bỏ qua | Client sinh tự động có thể gửi request bị backend từ chối. [OpenAPI](https://github.com/supportflow-ai/ai-it-service-desk/blob/bf38ef903f46f6ea21f80da44c11d437391a9efb/contracts/backend/openapi-baseline.json) |

## Cập nhật sau bản chụp (13/11/2026)

Các bảng ở trên mô tả mốc 05/11/2026. Những thay đổi sau đó ở backend, đối chiếu với `dev@07ce07a`:

- **Phạm vi đọc của Agent** (B1-PR3, backend #64, [ADR-016](https://github.com/supportflow-ai/ai-it-service-desk/blob/main/docs/adr/ADR-016-support-team-routing-and-agent-scope.md)): Agent chỉ đọc phiếu thuộc nhóm hỗ trợ đang hoạt động mà mình là thành viên, hoặc phiếu được phân công trực tiếp. Bộ lọc áp dụng cho chi tiết, hàng đợi và số lượng, timeline, tệp và lệnh của nhân viên; phiếu ngoài phạm vi trả `404`. Admin đọc toàn hệ thống. Vì vậy cụm "staff xem toàn hệ thống" và hàng đợi "mọi phiếu" trong các bảng trên chỉ đúng với Admin ở mốc hiện tại. Chưa có API quản trị nhóm hỗ trợ.
- **Tệp đính kèm** (backend #65): hạn mức tệp theo phiếu và xử lý lock timeout khi xác nhận; `POST /tickets/{id}/attachments/confirm` đổi chi tiết phản hồi trong OpenAPI.
- **Endpoint ngoài bảng MVP:** `POST /auth/refresh`, `/auth/revoke`, `/auth/change-password`, `/auth/forgot-password`, `/auth/reset-password`, `GET /departments`, `PUT /users/{id}/roles` và nhóm `/knowledge/articles` (nháp, xuất bản, lưu trữ, chi tiết, tìm kiếm) đã có ở backend. Đường dẫn đầy đủ nằm trong [OpenAPI backend](https://github.com/supportflow-ai/ai-it-service-desk/blob/main/contracts/backend/openapi-baseline.json).

Snapshot OpenAPI của web chưa theo kịp các thay đổi này; xem mục "Lệch còn mở" ở [tài liệu chung](README.md#rà-soát-lại-ngày-13112026).

## Giao tiếp Backend–AI

Backend công bố [hợp đồng phân loại v1](https://github.com/supportflow-ai/ai-it-service-desk/blob/bf38ef903f46f6ea21f80da44c11d437391a9efb/contracts/ai/v1/openapi.yaml). Hai bản hợp đồng ở Backend và AI Service khớp từng byte tại mốc rà soát. `POST /v1/ticket-classifications` dùng Bearer riêng giữa các dịch vụ. Backend tính `inputHash`. AI Service kiểm tra định dạng và trả lại nguyên giá trị cùng `requestId`, `ticketId`, `ticketRevision`. Phản hồi chỉ gồm gợi ý phân loại theo hợp đồng. Quyền thay đổi ticket thuộc backend. [Bản ghim AI](https://github.com/supportflow-ai/ai-service/blob/7c0910298c35150cb28ed2a71605b8c4e03a3938/contract.lock.json) · [Căn chỉnh backend–AI](https://github.com/supportflow-ai/ai-service/blob/7c0910298c35150cb28ed2a71605b8c4e03a3938/docs/backend-alignment.md)
