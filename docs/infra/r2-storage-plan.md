# Kế hoạch chuyển lưu trữ tệp sang Cloudflare R2 (hạ tầng)

Trạng thái: kế hoạch đề xuất chờ chủ dự án duyệt, chưa triển khai. Cập nhật 2026-11-13, đối chiếu `main` tại `cf1cb16` (cộng nhánh `fix/infra-backend-hosts-layout`). Quyết định và thiết kế nằm ở ADR-017 của kho backend (`docs/adr/ADR-017-cloudflare-r2-object-storage.md`). Kế hoạch các kho khác: backend (`docs/architecture/r2-storage-plan.md`), web (`docs/architecture/r2-upload-plan.md`), ai-service (`docs/r2-impact.md`). Mọi giá và giới hạn lấy từ tài liệu chính thức của Cloudflare, tra cứu 2026-11-13, nguồn ở cuối.

Chỉ dẫn của chủ dự án (2026-11-13): dùng hoàn toàn cơ chế tải lên, lưu trữ và xác nhận tệp của R2; trong lúc phát triển cả nhóm dùng chung khóa qua `.env`; dữ liệu MinIO cũ không chuyển; **thông tin tài khoản và endpoint R2 không đưa lên Git**.

## 1. Việc của kho này

Kho infra không chứa mã tải tệp. Việc của kho gồm: bỏ MinIO khỏi Compose, NGINX, CI và tài liệu; cung cấp biến môi trường `R2_*` cho API và Worker; ghi quy trình tạo bucket, token, CORS, vòng đời; bảo vệ khóa; và kiểm chứng toàn hệ thống với R2 trong CI.

## 2. Chi phí

### 2.1 Đơn giá (Standard storage)

| Hạng mục | Giá | Miễn phí mỗi tháng |
| --- | --- | --- |
| Dung lượng | 0,015 USD mỗi GB-tháng (tính trung bình đỉnh theo ngày trong 30 ngày) | 10 GB-tháng |
| Thao tác loại A (ghi, sao chép, liệt kê: `PutObject`, `CopyObject`, `ListObjects`…) | 4,50 USD mỗi triệu | 1 triệu |
| Thao tác loại B (đọc: `GetObject`, `HeadObject`…) | 0,36 USD mỗi triệu | 10 triệu |
| Thao tác miễn phí | `DeleteObject`, `DeleteBucket`, `AbortMultipartUpload` | không giới hạn |
| Băng thông ra (egress) | **Không tính phí**, kể cả qua S3 API và `r2.dev` | không giới hạn |

Lưu ý tính phí: mức dùng được làm tròn lên đơn vị tính phí kế tiếp; `PutObject` bị từ chối 412 vì điều kiện vẫn tính là loại A; yêu cầu bị từ chối vì thiếu quyền (401) không tính phí (câu này có trong bản tài liệu cũ, cần xác nhận lại trên trang giá hiện hành). Hạng Infrequent Access đắt hơn về thao tác và không dùng ở đây. Việc **ký presigned URL không gọi R2** nên không phát sinh phí.

### 2.2 Số thao tác theo luồng của hệ thống

| Luồng | Thao tác R2 | Loại A | Loại B |
| --- | --- | --- | --- |
| Tải lên và xác nhận một tệp | `PUT` (trình duyệt), `HEAD` khi xác nhận, `COPY`, `HEAD` kiểm lại, `DELETE` object tạm | 2 | 2 |
| Tải lên rồi bỏ dở | `PUT`; vòng đời xóa sau | 1 | 0 |
| Một lượt tải xuống | `GET` qua URL ký | 0 | 1 |

### 2.3 Ước tính theo ba quy mô

Giả định để tính, **không phải số đo thực tế**: dung lượng là tổng đang lưu cuối tháng; mọi tệp tải lên đều được xác nhận.

| Quy mô | Lưu trữ | Tải lên/tháng | Tải xuống/tháng | Loại A | Loại B | Chi phí/tháng |
| --- | --- | --- | --- | --- | --- | --- |
| Nhóm phát triển | 2 GB | 5.000 | 20.000 | 10.000 | 30.000 | **0 USD** (trong mức miễn phí) |
| Thử nghiệm nội bộ | 50 GB | 100.000 | 500.000 | 200.000 | 700.000 | **≈ 0,60 USD** (40 GB × 0,015; thao tác trong mức miễn phí) |
| Vận hành lớn | 500 GB | 1.000.000 | 5.000.000 | 2.000.000 | 7.000.000 | **≈ 11,85 USD** (490 GB × 0,015 = 7,35; loại A vượt 1 triệu × 4,50 = 4,50; loại B trong mức miễn phí) |

Với giới hạn hiện tại (10 MiB mỗi tệp, 10 tệp và 50 MiB mỗi phiếu), chi phí chủ yếu theo dung lượng lưu và số lượt ghi. Nhận xét: không có phí băng thông nên số lượt tải xuống gần như không đổi chi phí; rủi ro chi phí thật nằm ở **ghi hàng loạt** và **dung lượng không được dọn**, không phải ở lượt đọc. Kết luận này phụ thuộc giá hiện hành; trước khi phát hành cần tra lại trang giá.

Rủi ro cần canh: nếu R2 không ép dung lượng lúc `PUT` (đang kiểm chứng, xem ADR-017), một client độc hại có thể ghi tệp lớn hơn khai báo (tối đa gần 5 GiB cho một PUT theo tài liệu giới hạn) vào `uploads/pending/` trước khi bị bước xác nhận hoặc vòng đời dọn. Giảm thiểu: token chỉ cấp URL ngắn hạn qua backend đã kiểm quyền, quy tắc vòng đời, và theo dõi dung lượng bucket.

## 3. Truy cập công khai

Bucket R2 mặc định riêng tư. Có ba cách cho phép truy cập từ bên ngoài:

| Cách | Đặc điểm theo tài liệu R2 | Dùng cho tệp phiếu? |
| --- | --- | --- |
| **Bucket riêng và presigned GET** | URL do backend ký, hiệu lực từ 1 giây đến 7 ngày, ai có URL đều dùng được đến khi hết hạn | **Có (được chọn)** |
| `r2.dev` | Chỉ dành cho phát triển; bị giới hạn tốc độ (hàng trăm yêu cầu mỗi giây thì trả 429); không có cache, WAF, Bot Management | Không. Phải giữ tắt |
| Tên miền tùy chỉnh công khai | Có cache, WAF, kiểm soát truy cập; gắn tên miền mà chưa tạo ứng dụng Cloudflare Access thì **bucket thành công khai** | Không cho tệp phiếu |
| Tên miền tùy chỉnh và Cloudflare Access | Dành cho người dùng nội bộ của tổ chức | Không: người yêu cầu (Requester) là người ngoài |

Quyết định: bucket tệp phiếu **không bật `r2.dev`, không gắn tên miền tùy chỉnh**. Mọi lượt tải xuống đi qua `GET …/attachments/download-url` của backend, nơi kiểm quyền theo phiếu rồi ký URL hạn ngắn (đề xuất 300 giây). Nếu sau này có tệp thật sự công khai (ảnh tĩnh, tài liệu công bố), dùng **bucket riêng** có tên miền riêng và cache, tách khỏi bucket tệp phiếu.

Kiểm tra định kỳ: trang cài đặt bucket không có "Public Development URL" và không có "Custom Domain". Hạn chế rủi ro của URL ký: không ghi URL vào log, không dán vào chat hay ticket, chỉ dùng HTTPS, hạn ngắn.

Chưa xác nhận trong đợt tra cứu: presigned URL có hoạt động trên tên miền tùy chỉnh và việc cache có áp dụng cho URL ký hay không. Không ảnh hưởng quyết định ở trên vì không dùng tên miền tùy chỉnh cho tệp phiếu.

## 4. Mô hình bucket, token và khóa

| Môi trường | Bucket (tên đề xuất) | Token | Ai giữ |
| --- | --- | --- | --- |
| Phát triển (cả nhóm) | `supportflow-dev` | Một token Object Read & Write, giới hạn đúng bucket này | Cả nhóm, qua `.env` cục bộ |
| CI | `supportflow-ci` | Token riêng | Kho bí mật của GitHub Actions |
| Staging | `supportflow-staging` | Token riêng | Người vận hành, tệp môi trường trên máy chủ |
| Production | `supportflow-prod` | Token riêng | Chỉ người vận hành production |

- Token S3 của R2: Access Key ID là ID của token, Secret Access Key chỉ hiện một lần khi tạo. Quyền Object Read & Write cho đọc, ghi, liệt kê trong các bucket được chọn và chỉ dùng qua S3 API.
- Token do người dùng tạo sẽ mất hiệu lực khi người đó bị gỡ khỏi tài khoản (theo tài liệu R2): dùng token thuộc tài khoản cho khóa dùng chung của nhóm.
- Endpoint S3 có dạng `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`, tức chứa account ID. Coi endpoint như cấu hình nhạy cảm, đặt trong `.env`, không viết giá trị thật vào tài liệu hay mã.
- Ứng dụng không cần quyền tạo bucket: ops tạo bucket, CORS và vòng đời một lần.
- Khóa production không bao giờ nằm trên máy lập trình viên.

### 4.1 Cấp khóa dùng chung cho nhóm (giai đoạn phát triển)

1. Chủ tài khoản Cloudflare tạo bucket `supportflow-dev`, áp CORS và vòng đời (mục 5).
2. Tạo token thuộc tài khoản, quyền Object Read & Write, chỉ áp dụng cho bucket đó.
3. Lưu Access Key ID, Secret Access Key, Endpoint vào trình quản lý mật khẩu của nhóm (hoặc kênh tương đương); không gửi qua chat công khai, email, issue hay PR.
4. Mỗi thành viên sao chép `example.env` thành `.env` rồi điền bốn biến: `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`. Thành viên không làm việc với tệp có thể bỏ trống (backend sẽ báo tính năng tệp không khả dụng, các tính năng khác chạy bình thường).
5. Kiểm tra `git status` không theo dõi `.env`; không dán nội dung `.env` vào log hay ảnh chụp.

Hạn chế đã chấp nhận: dùng chung một danh tính nên không phân biệt được ai làm gì trong nhật ký R2, và một khóa lộ ảnh hưởng cả nhóm. Vì vậy chỉ dùng bucket `dev` với dữ liệu thử, không dùng khóa này ở nơi khác, và xoay hoặc thu hồi khi kết thúc giai đoạn phát triển (giai đoạn 5).

### 4.2 Khi nghi ngờ lộ khóa

Thu hồi token ngay trên Cloudflare, tạo token mới và phát lại cho nhóm, rà danh sách object và mức dùng của bucket để tìm ghi, xóa lạ. Việc xóa khóa khỏi lịch sử Git không đủ vì khóa đã bị coi là lộ.

### 4.3 Chặn khóa lọt vào Git

- **Quét bí mật và bảo vệ khi push (push protection) của GitHub đã được bật ở cả bốn kho ngày 2026-11-13** (trước đó đang tắt; các kho đều công khai). Kiểm tra lại bằng `gh api repos/supportflow-ai/<kho>` (trường `security_and_analysis`).
- `.gitignore` của backend và web mới bỏ qua `.env`, `.env.local`, `.env.*.local`; thiếu `.env.staging`, `.env.production`. Hai kho này cần thêm `.env.*` kèm `!.env.example`. Kho infra và ai-service đã có.
- `example.env`, `.env.example` chỉ chứa chỗ giữ chỗ (`<ACCOUNT_ID>`, `<ACCESS_KEY_ID>`); Compose dùng cú pháp bắt buộc `${R2_ENDPOINT:?Set R2_ENDPOINT}` để thiếu biến thì dừng thay vì dùng giá trị mặc định.
- Tùy chọn: một bước quét bí mật trong CI (ví dụ gitleaks) làm lớp bảo vệ thứ hai.

## 5. Bucket: CORS và vòng đời

Cấu hình một lần cho mỗi bucket (bảng điều khiển Cloudflare, hoặc API). Các mẫu dưới đây **cần đối chiếu với trang CORS và vòng đời hiện hành của R2 trước khi áp dụng**, vì định dạng nhập khác nhau giữa bảng điều khiển và API.

CORS cho bucket `dev` (tải lên từ trình duyệt bằng PUT ký sẵn):

```json
[
  {
    "AllowedOrigins": ["http://localhost:5173"],
    "AllowedMethods": ["PUT"],
    "AllowedHeaders": ["Content-Type"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

- `AllowedOrigins` là `scheme://host[:port]`, không có path. Mỗi môi trường chỉ liệt kê origin web của chính nó (staging, production dùng origin riêng). Đổi origin của web thì phải sửa CORS.
- Tải xuống mở bằng liên kết điều hướng nên không cần CORS; chỉ thêm `GET`, `HEAD` nếu web đọc bằng `fetch`.
- URL hết hạn trả 403 `ExpiredRequest` **không kèm tiêu đề CORS**, nên trình duyệt chỉ báo lỗi mạng.

Vòng đời (đã có sẵn mẫu ở `storage/pending-upload-lifecycle.json`, giữ làm đặc tả): xóa object ở `uploads/pending/` sau 1 ngày. Xóa theo vòng đời thường hoàn tất trong khoảng 24 giờ; tối đa 1.000 quy tắc mỗi bucket. Mặc định R2 tự hủy upload nhiều phần dở dang sau 7 ngày. Với bucket `dev` cân nhắc thêm quy tắc xóa mọi object sau 30 ngày để khỏi tích tụ.

## 6. Việc phải làm trong kho

### 6.1 Gỡ MinIO

| Nhóm | Tệp |
| --- | --- |
| Dịch vụ Compose | `minio` và `minio-init` trong `docker-compose.yml`, `compose.yaml`, `deploy/compose.system.yml`, `deploy/compose.release.yml`; volume và phụ thuộc `minio-init` của API, Worker |
| Build và script | `deploy/minio/Dockerfile`, `scripts/init_minio_buckets.sh`, phần liên quan trong `scripts/wait_for_services.sh` |
| NGINX | Khối `server { listen 9000; … proxy_pass http://minio:9000 }` trong `nginx/conf.d/default.conf`; cổng 9000 và `STORAGE_*` ở Compose. Trình duyệt tải thẳng lên R2 nên gateway không còn thấy dữ liệu tệp |
| Kiểm thử | `tests/unit/test_minio_init.py`, `tests/integration/test_minio_live.py`, `tests/integration/compose.minio.yml`; các khẳng định về `minio-init` trong `tests/unit/test_release_manifest.py` |
| CI | Job `minio-integration`, tham số `--add-host minio:127.0.0.1` ở bước kiểm tra NGINX |
| Biến môi trường | `MINIO_*`, `STORAGE_*`, `Minio__*` trong `example.env`, `.env.example`, `.env.local.example`, `deploy/example.env`, `deploy/.env.example`, `compose.local.yaml` |

### 6.2 Thêm R2

- Biến trong `.env`: `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`. Compose ánh xạ sang `R2__Endpoint`, `R2__AccessKeyId`, `R2__SecretAccessKey`, `R2__Bucket` cho API và Worker bằng cú pháp bắt buộc `${…:?}`. Giá trị thật không bao giờ nằm trong tệp được Git theo dõi.
- Bản `docker-compose.yml` cho lập trình viên chỉ còn PostgreSQL (pgvector) và Mailpit; lưu tệp dùng R2 từ máy chủ API đang chạy trên máy.
- CI: bước kiểm chứng tệp trong smoke dùng bucket `supportflow-ci` và tiền tố theo lần chạy; chỉ chạy khi có bí mật, **bỏ qua với PR từ fork** (GitHub không cấp bí mật cho fork). Smoke còn lại không cần khóa. Job không được in biến môi trường hay URL ký ra log.
- `sources.lock.json` và digest: **không đổi** cho tới khi có quyết định phát hành; bản phát hành mới phải ghim SHA backend và web đã chuyển sang R2.
- Cập nhật tài liệu: `README.md`, `deploy/README.md`, `docs/infra/local-development.md`, `docs/infra/operations-runbook.md` (mục 2 hiện hướng dẫn `mc` của MinIO), `docs/infra/repository-boundaries.md`, `docs/release-and-storage.md`, `docs/project/README.md` (sơ đồ và đoạn nhắc MinIO), `AGENTS.md`, [cẩm nang chung](../team-handbook.md) (bốn kho cùng lúc). `docs/infra/refactor-progress.md` là lịch sử, giữ nguyên.

### 6.3 Vận hành R2

Theo dõi dung lượng và số thao tác của từng bucket trên bảng điều khiển để so với mức miễn phí; kiểm tra thông báo hoặc cảnh báo chi phí hiện có trong tài khoản (chưa xác nhận tính năng cụ thể). Sao lưu và quyền xóa nhầm của tệp đã xác nhận là quyết định còn mở (mục 8). Sổ tay vận hành phải thay mục MinIO bằng các thao tác tương đương: xem danh sách object, xem dung lượng, xoay token, kiểm tra CORS và vòng đời.

## 7. Lộ trình (phần hạ tầng)

| Giai đoạn | Việc của kho infra | Điều kiện xong |
| --- | --- | --- |
| 0 | Tạo bucket `dev`, token, CORS, vòng đời; hỗ trợ kiểm chứng của backend | Bucket `dev` hoạt động; ghi kết quả |
| 1–2 | Chưa đổi Compose (backend và web đang chuyển) | – |
| 3 | Gỡ MinIO, thêm `R2_*`, đổi CI và kiểm thử; tạo bucket và bí mật cho CI | Smoke đạt với bucket `ci` |
| 4 | Phát khóa `dev` cho nhóm, bật quét bí mật, cập nhật tài liệu | Thành viên mới dựng được môi trường chỉ từ tài liệu |
| 5 | Bucket và token riêng cho staging, production; xoay hoặc thu hồi khóa `dev`; chốt sao lưu | Chủ dự án duyệt |

Điểm không quay lại: sau giai đoạn 3. Trước đó mọi thay đổi hạ tầng hoàn nguyên được bằng revert.

## 8. Quyết định còn mở

1. Loại token cho nhóm: thuộc tài khoản hay thuộc người tạo.
2. Tên bucket và tài khoản Cloudflare dùng cho từng môi trường; ai giữ quyền quản trị tài khoản.
3. Sao lưu, lưu giữ và quyền xóa tệp đã xác nhận (phần còn mở của DEC-07).
4. Quy tắc xóa tự động của bucket `dev` (30 ngày hay không).
5. Có thêm bước quét bí mật trong CI hay không.

## Nguồn (Cloudflare, tra cứu 2026-11-13)

- [Giá R2](https://developers.cloudflare.com/r2/pricing/)
- [Presigned URL](https://developers.cloudflare.com/r2/api/s3/presigned-urls/)
- [Bucket công khai](https://developers.cloudflare.com/r2/buckets/public-buckets/) và [R2 với Cloudflare Access](https://developers.cloudflare.com/r2/tutorials/cloudflare-access/)
- [Giới hạn](https://developers.cloudflare.com/r2/platform/limits/)
- [CORS](https://developers.cloudflare.com/r2/buckets/cors/)
- [Vòng đời đối tượng](https://developers.cloudflare.com/r2/buckets/object-lifecycles/)
- [Token và khóa S3](https://developers.cloudflare.com/r2/api/tokens/)
