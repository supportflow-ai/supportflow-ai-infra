# Ranh giới trách nhiệm giữa các Repository (Repository Boundaries)

Tài liệu này xác định ranh giới sở hữu, phân quyền công nghệ và giao thức cộng tác giữa 4 repository thuộc tổ chức `supportflow-ai`.

[Tài liệu chung và mốc mã nguồn](../project/README.md) · [Đối chiếu API Backend–AI](../project/api-and-access.md)

---

## 1. Ma trận sở hữu (Ownership Matrix)

| Repository | Công nghệ chính | Trách nhiệm sở hữu độc quyền | Không được can thiệp |
|---|---|---|---|
| **`ai-it-service-desk`** | .NET (C#) Clean Architecture | - Toàn quyền sở hữu Schema Database (EF Core)<br>- Quản lý phiên bản migration cơ sở dữ liệu<br>- Quyền hạn tạo phiếu, đổi trạng thái phiếu<br>- Phát hành JWT và xác thực người dùng<br>- Thẩm quyền quyết định áp dụng gợi ý AI | - Không chứa mã giao diện React<br>- Không chứa logic huấn luyện/inference ML nặng<br>- Không chứa file cấu hình NGINX gateway toàn hệ thống |
| **`ai-it-service-desk-web`** | React 19, TypeScript, Vite, AntD | Giao diện SPA, điều hướng và dữ liệu truy vấn qua TanStack Query. Sở hữu giao diện duyệt gợi ý khi luồng này được triển khai | Web gọi API nghiệp vụ của Backend. UI dùng phản hồi thực của API trong môi trường phát hành |
| **`ai-service`** | Python 3.12, FastAPI, Ports & Adapters | Gợi ý danh mục, mức độ ảnh hưởng, độ khẩn cấp theo hợp đồng v1. Có hai bộ cung cấp `rule` và `noop` | Chỉ nhận yêu cầu S2S nội bộ. Quyền, trạng thái phiếu và database nghiệp vụ thuộc Backend |
| **`supportflow-ai-infra`** | Docker Compose, NGINX, Python, Shell | - Môi trường phụ trợ Local Dev (PostgreSQL 17, MinIO)<br>- NGINX reverse proxy & cân bằng tải 2 node API (ADR-008)<br>- Kịch bản kiểm thử toàn hệ thống (Smoke Tests)<br>- Runbook vận hành và quy chuẩn mạng Docker | - Không sở hữu file migration SQL/EF Core<br>- Không sửa đổi mã nghiệp vụ ứng dụng |

---

## 2. Các nguyên tắc bất biến (Architectural Invariants)

### 2.1. Quản lý Cơ sở dữ liệu và Schema
- Repository `ai-it-service-desk` sở hữu schema. `ServiceDesk.Platform` chứa EF Core migration và `ServiceDesk.Migrator` cung cấp lệnh vận hành.
- Repo `supportflow-ai-infra` chỉ cung cấp container PostgreSQL 17 sạch, không bao giờ chứa script DDL tạo bảng nghiệp vụ.

### 2.2. Giao tiếp Dịch vụ AI (ADR-012)
- Toàn bộ giao tiếp giữa Backend và AI Service phải tuân theo hợp đồng `contracts/ai/v1/openapi.yaml`.
- Backend băm tiêu đề và mô tả theo thuật toán `ai-input-v2`, gửi kèm `inputHash`.
- `ai-service` kiểm tra định dạng `inputHash` và trả nguyên giá trị theo hợp đồng. Backend đối chiếu các trường định danh và mã băm của phản hồi.
- Hợp đồng chỉ trả gợi ý phân loại. Khi triển khai quy trình duyệt, nhân viên hỗ trợ quyết định chấp nhận hay từ chối qua Backend.

### 2.3. Ranh giới mạng và Gateway (ADR-008)
- NGINX đóng vai trò cổng vào duy nhất (Single Ingress Gateway):
  - Chuyển tiếp `/` vào `web`.
  - Chuyển tiếp `/api/` vào `backend_cluster` (`api-1:8080` và `api-2:8080`).
  - Chặn triệt để mọi truy cập từ bên ngoài vào `/internal/` và port của `ai-service`.
