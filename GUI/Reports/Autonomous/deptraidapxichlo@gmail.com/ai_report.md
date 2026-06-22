# Báo cáo Tình báo OSINT: deptraidapxichlo@gmail.com

> Được tạo bởi Mr.Holmes Autonomous Profiler — Model: gemini-2.5-flash-nothinking
> Ngày: 05/04/2026 | 43 entities, 52 relationships

## 1. Tóm tắt điều hành

Mục tiêu, **deptraidapxichlo@gmail.com**, là một cá nhân có hoạt động trực tuyến rộng khắp, đặc biệt là trong các diễn đàn và dịch vụ của Việt Nam, cũng như các nền tảng quốc tế về công nghệ, giải trí và phong cách sống. Email và username "deptraidapxichlo" đã bị lộ trong nhiều vụ rò rỉ dữ liệu lớn, cho thấy mức độ phơi nhiễm thông tin cá nhân cao.

Phân tích hành vi cho thấy mục tiêu là một người dùng có kỹ năng kỹ thuật (Python, Docker, cybersecurity), có sở thích đa dạng từ âm nhạc (DJ, house music), game, thời trang, đến chia sẻ tài liệu và tham gia các diễn đàn cộng đồng. Việc sử dụng username nhất quán trên nhiều nền tảng cho thấy một nỗ lực có ý thức trong việc xây dựng và duy trì danh tính trực tuyến.

Mức độ rủi ro tổng thể được đánh giá là **Trung bình đến Cao** do sự phơi nhiễm dữ liệu đáng kể và sự hiện diện rộng rãi trên các nền tảng, tạo ra nhiều điểm yếu tiềm năng cho các cuộc tấn công kỹ thuật xã hội hoặc chiếm đoạt tài khoản.

## 2. Các thực thể được phát hiện

**Email:**
* deptraidapxichlo@gmail.com

**Username:**
* deptraidapxichlo

**Các nền tảng bị lộ dữ liệu (Breach/Leak Data):**
* adobe.com (2013)
* dropbox.com (2012)
* giaiphapexcel.com
* gonitro.com
* zynga.com (2019)
* adultfriendfinder.com (2016)
* gamevn.com
* tailieu.vn
* zing.vn
* verifications.io, pureincubation.com, apollo.io, peopledatalabs (data brokers)
* intelx.io-pastescrape, naz.api, antipublic-combo (paste databases)
* canva.com, deezer.com, substack.com, luminpdf.com, evite.com, mgmresorts.com

**Các nền tảng có hồ sơ trực tuyến (19 sites tìm thấy):**
* YouTube, Pinterest, WordPress, Archive.org, Interpals
* TryHackMe, PyPi, DockerHub, AudioJungle, ThemeForest
* House-Mixes, Ko-Fi, Roblox, Quotev, Listal.com
* Quizsilo, 21Buttons, MyMonat, Passes

## 3. Mối quan hệ quan trọng

* **deptraidapxichlo@gmail.com** → **deptraidapxichlo** (auto:email-prefix)
* **deptraidapxichlo@gmail.com** → 5 breach domains (LeakLookup)
* **deptraidapxichlo** → adultfriendfinder.com, gamevn.com, tailieu.vn, zing.vn (LeakLookup)
* **deptraidapxichlo** → 19 social platforms (MrHolmes:username-scanner)
* Email xuất hiện trong: verifications.io, apollo.io, peopledatalabs → data broker profiles đang tồn tại

## 4. Phân tích hành vi & sở thích

* **Kỹ năng kỹ thuật & Phát triển:** PyPi (Python developer), DockerHub (container dev), TryHackMe (học cybersecurity) → lập trình viên có quan tâm bảo mật
* **Sáng tạo nội dung:** YouTube, AudioJungle, ThemeForest, House-Mixes → tạo/chia sẻ nội dung đa phương tiện, nhạc DJ/house
* **Cộng đồng & Giao tiếp:** gamevn.com, giaiphapexcel.com, Interpals → tham gia cộng đồng, pen pals quốc tế
* **Sở thích cá nhân đa dạng:** game (Roblox, Zynga), thời trang (21Buttons), sức khỏe (MyMonat), tài liệu (tailieu.vn)
* **Nhận diện online nhất quán:** Username "deptraidapxichlo" = cụm từ tiếng Việt đùa vui → người Việt Nam, xây dựng identity chủ động
* **Hành vi rủi ro bảo mật:** Email bị lộ trong 5+ breaches lớn → khả năng cao tái sử dụng mật khẩu

## 5. Đánh giá rủi ro

| Rủi ro | Mức độ | Lý do |
|--------|--------|-------|
| Chiếm đoạt tài khoản (ATO) | **Cao** | Email lộ trong 5+ breach (adobe, dropbox, zynga...) |
| Tấn công kỹ thuật xã hội | **Trung bình-Cao** | 19 platform profiles, sở thích rõ ràng → dễ phishing nhắm mục tiêu |
| Lộ thông tin cá nhân (PII) | **Trung bình** | Data brokers (apollo.io, peopledatalabs) có hồ sơ tổng hợp |
| Rủi ro danh tiếng | **Thấp** | Xuất hiện trên AdultFriendFinder có thể nhạy cảm |
| Tấn công nhắm mục tiêu | **Trung bình** | Kỹ năng tech → tài sản có giá trị cho threat actors |

## 6. Bước tiếp theo được khuyến nghị

1. **Phân tích sâu các platform:** YouTube (@deptraidapxichlo), WordPress, PyPi packages → tìm thêm PII, liên kết, tên thật
2. **Truy vấn data brokers:** verifications.io, apollo.io, peopledatalabs → PII, số điện thoại, địa chỉ
3. **Sử dụng dorks đã tạo:**
   - `site:gamevn.com "deptraidapxichlo"` → posts/comments Việt Nam
   - `site:tailieu.vn "deptraidapxichlo"` → tài liệu đã upload
   - `"deptraidapxichlo@gmail.com" filetype:sql OR filetype:csv`
   - `"deptraidapxichlo" tên OR họ OR "full name"` → tìm tên thật
4. **Reverse image search:** Profile pics từ Pinterest, YouTube → xác minh danh tính
5. **GitHub/GitLab search:** Tìm repositories với username hoặc email → code commits có thể lộ tên thật, location
6. **Kiểm tra Canva, Deezer, Substack:** Các tài khoản có thể có profile public với thông tin thêm
