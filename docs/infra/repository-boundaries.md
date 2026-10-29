# Ranh giới trách nhiệm giữa các Repository (Repository Boundaries)

Tài liệu này xác định ranh giới sở hữu, phân quyền công nghệ và giao thức cộng tác giữa 4 repository thuộc tổ chức `supportflow-ai`.

---

## 1. Ma trận sở hữu (Ownership Matrix)

| Repository | Công nghệ chính | Trách nhiệm sở hữu độc quyền | Không được can thiệp |
|---|---|---|---|
| **`ai-it-service-desk`** | .NET (C#) Clean Architecture | - Toàn quyền sở hữu Schema Database (EF Core)<br>- Quản lý phiên bản migration cơ sở dữ liệu<br>- Quyền hạn tạo phiếu, đổi trạng thái phiếu<br>- Phát hành JWT và xác thực người dùng<br>- Thẩm quyền quyết định áp dụng gợi ý AI | - Không chứa mã giao diện React<br>- Không chứa logic huấn luyện/inference ML nặng<br>- Không chứa file cấu hình NGINX gateway toàn hệ thống |
| **`ai-it-service-desk-web`** | React 19, TypeScript, Vite, AntD | - Giao diện người dùng SPA<br>- Trải nghiệm phân loại phiếu (Human-in-the-loop)<br>- Quản lý trạng thái remote cache qua TanStack Query | - Không gọi trực tiếp AI Service (bắt buộc qua API Gateway / Backend)<br>- Không tự giả lập dữ liệu thành công trong production |
| **`ai-service`** | Python 3.12, FastAPI (Layered Modular) | - Phân loại danh mục, mức độ ảnh hưởng, độ khẩn cấp<br>- Thuật toán xác minh mã băm `ai-input-v2` SHA-256<br>- Động cơ phân loại 2 tầng: SLM + Rule Regex Triage | - **Bất biến P0**: CẤM kết nối trực tiếp Database nghiệp vụ<br>- CẤM tự ý ghi đè trạng thái vé hoặc phân quyền<br>- CẤM mở endpoint ra public Internet (chỉ nhận gọi nội bộ S2S) |
| **`supportflow-ai-infra`** | Docker Compose, NGINX, Python, Shell | - Môi trường phụ trợ Local Dev (PostgreSQL 16, MinIO)<br>- NGINX reverse proxy & cân bằng tải 2 node API (ADR-008)<br>- Kịch bản kiểm thử toàn hệ thống (Smoke Tests)<br>- Runbook vận hành và quy chuẩn mạng Docker | - Không sở hữu file migration SQL/EF Core<br>- Không sửa đổi mã nghiệp vụ ứng dụng |

---

## 2. Các nguyên tắc bất biến (Architectural Invariants)

### 2.1. Quản lý Cơ sở dữ liệu và Schema
- **Một nguồn chân lý duy nhất (SSOT)**: Repository `ai-it-service-desk` (thông qua project `ServiceDesk.Database` và `ServiceDesk.Infrastructure`) sở hữu 100% schema.
- Repo `supportflow-ai-infra` chỉ cung cấp container PostgreSQL 16 sạch, không bao giờ chứa script DDL tạo bảng nghiệp vụ.

### 2.2. Giao tiếp Dịch vụ AI (ADR-012)
- Toàn bộ giao tiếp giữa Backend và AI Service phải tuân theo hợp đồng `contracts/ai/v1/openapi.yaml`.
- Backend băm tiêu đề và mô tả theo thuật toán `ai-input-v2`, gửi kèm `inputHash`.
- `ai-service` xác thực `inputHash` trước khi xử lý. Nếu băm sai hoặc không khớp, trả về `400 Bad Request`.
- `ai-service` không có quyền thực hiện hành động (không trả về `action: "close"`). Quyết định chấp nhận hay từ chối phân loại thuộc về nhân viên hỗ trợ (Human-in-the-loop).

### 2.3. Ranh giới mạng và Gateway (ADR-008)
- NGINX đóng vai trò cổng vào duy nhất (Single Ingress Gateway):
  - Chuyển tiếp `/` vào `web`.
  - Chuyển tiếp `/api/` vào `backend_cluster` (`api-1:8080` và `api-2:8080`).
  - Chặn triệt để mọi truy cập từ bên ngoài vào `/internal/` và port của `ai-service`.
