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

## Sai lệch cần phối hợp

| Chủ đề | Bằng chứng tại các mốc đã ghim | Tác động và trạng thái |
| --- | --- | --- |
| Danh bạ Agent | Backend trả `userId`, `fullName`. Bộ đọc Web yêu cầu `email`. OpenAPI backend khai báo mảng đối tượng chung | Phản hồi có phần tử sẽ bị Web từ chối nếu thiếu `email`. Cần thống nhất schema danh bạ trước demo. [Backend](https://github.com/supportflow-ai/ai-it-service-desk/blob/bf38ef903f46f6ea21f80da44c11d437391a9efb/src/backend/ServiceDesk.Api/Endpoints/AuthEndpoints.cs) · [Web](https://github.com/supportflow-ai/ai-it-service-desk-web/blob/02136b6e09cfb912a612948bfec0b0243e981caf/src/features/tickets/api/ticketContract.ts) |
| Nhận xử lý | Use case cho Agent và Admin. Web chỉ hiển thị cho người có vai trò Agent | Admin chỉ có một vai trò sẽ thiếu nút thao tác trên Web. Chính sách tương lai cần được chủ dự án xác nhận. [Backend](https://github.com/supportflow-ai/ai-it-service-desk/blob/bf38ef903f46f6ea21f80da44c11d437391a9efb/src/backend/ServiceDesk.Application/Ticketing/ClaimTicket/ClaimTicketUseCase.cs) · [Web](https://github.com/supportflow-ai/ai-it-service-desk-web/blob/02136b6e09cfb912a612948bfec0b0243e981caf/src/features/tickets/model/ticketPermissions.ts) |
| Hủy phân công | Domain yêu cầu `Assigned`. Web có thể cho phép thao tác ở trạng thái khác nếu còn người phụ trách và phiếu chưa kết thúc | Nút có thể xuất hiện rồi bị backend từ chối. [Domain](https://github.com/supportflow-ai/ai-it-service-desk/blob/bf38ef903f46f6ea21f80da44c11d437391a9efb/src/backend/ServiceDesk.Domain/Ticketing/Ticket.cs) · [Web](https://github.com/supportflow-ai/ai-it-service-desk-web/blob/02136b6e09cfb912a612948bfec0b0243e981caf/src/features/tickets/model/ticketPermissions.ts) |
| Ưu tiên trong hàng đợi | Backend có tham số lọc và sắp xếp ưu tiên. Web đang khóa bộ lọc ưu tiên | Xác nhận phạm vi UI trước khi thêm bước lọc vào demo. [Web](https://github.com/supportflow-ai/ai-it-service-desk-web/blob/02136b6e09cfb912a612948bfec0b0243e981caf/src/features/tickets/components/AgentQueueToolbar.tsx) |
| Snapshot OpenAPI của Web | Snapshot ghim backend `007a258`. So với backend `main`, có khác biệt ở Knowledge, schema danh bạ, tham số hàng đợi và khai báo `UserInfo` | Kiểm tra nội bộ của Web xác nhận snapshot đã ghim. Khi phát hành chung, kiểm thêm với đúng bản backend dùng để chạy demo. [Nguồn snapshot](https://github.com/supportflow-ai/ai-it-service-desk-web/blob/02136b6e09cfb912a612948bfec0b0243e981caf/tests/contracts/backend-source.json) |
| Hợp đồng revision | Use case bắt buộc revision dương ở các lệnh trên. Một số khai báo trong OpenAPI còn cho phép bỏ qua | Client sinh tự động có thể gửi request bị backend từ chối. [OpenAPI](https://github.com/supportflow-ai/ai-it-service-desk/blob/bf38ef903f46f6ea21f80da44c11d437391a9efb/contracts/backend/openapi-baseline.json) |

## Giao tiếp Backend–AI

Backend công bố [hợp đồng phân loại v1](https://github.com/supportflow-ai/ai-it-service-desk/blob/bf38ef903f46f6ea21f80da44c11d437391a9efb/contracts/ai/v1/openapi.yaml). Hai bản hợp đồng ở Backend và AI Service khớp từng byte tại mốc rà soát. `POST /v1/ticket-classifications` dùng Bearer riêng giữa các dịch vụ. Backend tính `inputHash`. AI Service kiểm tra định dạng và trả lại nguyên giá trị cùng `requestId`, `ticketId`, `ticketRevision`. Phản hồi chỉ gồm gợi ý phân loại theo hợp đồng. Quyền thay đổi ticket thuộc backend. [Bản ghim AI](https://github.com/supportflow-ai/ai-service/blob/134c9d21287108ff923fffce5ad52a2cb6df3e48/contract.lock.json) · [Căn chỉnh backend–AI](https://github.com/supportflow-ai/ai-service/blob/134c9d21287108ff923fffce5ad52a2cb6df3e48/docs/backend-alignment.md)
