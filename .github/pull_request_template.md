## 1. Nội dung và lý do thay đổi

<!-- Nêu vấn đề, hành vi sau thay đổi và phạm vi chịu ảnh hưởng (Compose, NGINX, script, ghim phiên bản, tài liệu). -->

- Loại thay đổi: [ ] Tính năng  [ ] Sửa lỗi  [ ] Bảo trì  [ ] Tài liệu  [ ] Ghim phiên bản / phát hành
- Mã công việc hoặc liên kết (nếu có, không bắt buộc):

## 2. Bằng chứng kiểm thử

<!-- Ghi lệnh thực sự đã chạy, kết quả và SHA được kiểm chứng. Không chỉ đánh dấu ô. -->

```sh
docker compose --env-file example.env -f docker-compose.yml config --quiet
docker compose --env-file deploy/example.env -f deploy/compose.system.yml config --quiet
docker compose --env-file .env.local.example -f compose.yaml -f compose.local.yaml config --quiet
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -v   # cần Docker, khi đổi MinIO hoặc storage
```

- SHA đã kiểm chứng:
- Kết quả, số kiểm thử đạt/thất bại/bỏ qua:
- Smoke trên stack thật (nếu đổi NGINX, định tuyến, ghim phiên bản): SHA của từng kho đã dùng:
- Kiểm tra không chạy và lý do, nếu có:

## 3. Ảnh hưởng và rollback

Đối chiếu [cẩm nang chung](../docs/team-handbook.md#4-thay-đổi-ảnh-hưởng-kho-khác).

- [ ] Không đổi `sources.lock.json` hay digest. Nếu có đổi: đã có quyết định phát hành, SHA và digest đổi cùng nhau
- [ ] Không mở `/internal/` hay cổng ai-service ra ngoài NGINX
- [ ] Không thao tác lên staging, production hay volume có dữ liệu thật
- Cách rollback nếu có tác động tới vận hành hoặc dữ liệu:

## 4. Điều kiện hoàn thành

- [ ] CI đạt trên commit mới nhất của PR (kiểm tra Compose, NGINX, MinIO thật, smoke)
- [ ] Có ít nhất một người khác đánh giá; không tự phê duyệt PR của mình
- [ ] Tài liệu liên quan đã cập nhật bằng tiếng Việt, hoặc nêu lý do không cần:
- [ ] Không có bí mật thật trong Git, log hay ảnh chụp
- [ ] Không sửa test hay cấu hình để làm CI xanh
