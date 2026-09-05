"""Vietnamese editorial knowledge and authored demo exercises. Not vendor configuration guides."""
from pathlib import Path
import json,sqlite3
ROOT=Path(__file__).parent
CHECKED='2026-09-05'
SOURCES={
'csf':('NIST CSF 2.0','https://www.nist.gov/cyberframework/faqs'),
'ir':('NIST SP 800-61 Rev. 3 (2025)','https://csrc.nist.gov/pubs/sp/800/61/r3/final'),
'zt':('NIST SP 800-207','https://csrc.nist.gov/pubs/sp/800/207/final'),
'ransom':('CISA #StopRansomware Guide','https://www.cisa.gov/stopransomware/ransomware-guide'),
'mfa':('CISA Implementing Phishing-Resistant MFA','https://www.cisa.gov/sites/default/files/2023-01/fact-sheet-implementing-phishing-resistant-mfa-508c.pdf'),
'kev':('CISA Known Exploited Vulnerabilities Catalog','https://www.cisa.gov/known-exploited-vulnerabilities-catalog'),
'web':('OWASP Top 10:2025','https://owasp.org/Top10/2025/'),
'api':('OWASP API Security Top 10:2023','https://owasp.org/API-Security/editions/2023/en/0x11-t10/'),
'log':('OWASP Logging Cheat Sheet','https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html'),
'secret':('OWASP Secrets Management Cheat Sheet','https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html'),
'container':('OWASP Docker Security Cheat Sheet','https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html'),
'ai':('OWASP LLM Prompt Injection Prevention','https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html'),
'attack':('MITRE ATT&CK','https://attack.mitre.org/')}

# Topic, category, reference, explanation, discovery questions, authored workflow, evidence, limit.
TOPICS=[
('CSF','Quản trị rủi ro theo NIST CSF 2.0','Quản trị ATTT','csf',
'CSF 2.0 tổ chức kết quả an ninh theo Govern, Identify, Protect, Detect, Respond, Recover. Có thể so sánh hiện trạng và mục tiêu để ưu tiên khoảng trống. Đây là khung quản trị, không phải chứng chỉ sản phẩm.',
'Dịch vụ nào quan trọng nhất? Ai sở hữu rủi ro? Mất dữ liệu hoặc ngừng hoạt động ảnh hưởng gì?',
'Liệt kê 5 dịch vụ trọng yếu và chủ sở hữu|Ghi hiện trạng cùng bằng chứng cho từng chức năng|Chọn khoảng trống có ảnh hưởng lớn|Lập kế hoạch với owner, hạn xử lý và tiêu chí đo',
'Bảng hiện trạng/mục tiêu; risk register; kế hoạch ưu tiên.', 'Không khẳng định đạt chuẩn chỉ vì đã mua firewall hoặc hoàn thành checklist.'),
('RISK','Đánh giá rủi ro và phân loại tài sản','Quản trị ATTT','csf',
'Rủi ro cần xét tài sản, tình huống đe dọa, điểm yếu và tác động kinh doanh. Mức chấp nhận rủi ro do tổ chức quyết định; đầu tư bảo vệ phải gắn với dữ liệu và dịch vụ cần duy trì.',
'Tài sản nào chứa dữ liệu khách? Có owner và phụ thuộc bên ngoài không?',
'Tạo inventory kèm owner và loại dữ liệu|Mô tả tình huống mất bí mật, toàn vẹn, sẵn sàng|Chấm tác động và khả năng theo thang nội bộ|Ghi kiểm soát hiện có và người chấp nhận phần rủi ro còn lại',
'Inventory; ma trận rủi ro; quyết định xử lý hoặc chấp nhận.', 'Không dùng một điểm số chung thay đánh giá nghiệp vụ.'),
('MFA','MFA và xác thực chống phishing','Danh tính & truy cập','mfa',
'MFA dùng nhiều yếu tố xác thực; các phương pháp có khả năng chống phishing khác nhau. FIDO2/WebAuthn hỗ trợ xác thực chống phishing. SMS, OTP hoặc push thông thường không tự có mức bảo vệ tương đương.',
'Nhân viên đăng nhập email, VPN, SaaS bằng gì? Tài khoản quản trị có MFA? Mất thiết bị thì khôi phục ra sao?',
'Thống kê ứng dụng và nhóm người dùng|Pilot phương thức tương thích trên nhóm nhỏ|Thử đăng nhập, mất thiết bị và khôi phục có xác minh|Đánh giá log và mở rộng theo đợt',
'Ma trận ứng dụng/MFA; kết quả pilot; quy trình cấp lại.', 'Không yêu cầu khách gửi mã OTP, recovery code hoặc mật khẩu cho sale/AI.'),
('IAM','IAM, quyền tối thiểu và vòng đời tài khoản','Danh tính & truy cập','zt',
'Xác thực xác minh danh tính; phân quyền quyết định tài nguyên và hành động được phép. Quyền nên bám nhiệm vụ, thay đổi khi chuyển vị trí và thu hồi khi nghỉ việc.',
'Ai duyệt cấp quyền? Có tài khoản dùng chung? Quyền trên ứng dụng có đồng bộ với danh tính trung tâm?',
'Lập ma trận vai trò và tài nguyên cho nhóm sale/kỹ thuật|Thử người đúng vai trò và người khác vai trò|Mô phỏng chuyển bộ phận và nghỉ việc|Đối chiếu quyền còn tồn tại sau thu hồi',
'Ma trận quyền; ticket cấp/thu hồi; bằng chứng kiểm truy cập.', 'SSO không tự chứng minh phân quyền đúng ở từng ứng dụng.'),
('PAM','PAM và kiểm soát tài khoản đặc quyền','Danh tính & truy cập','zt',
'Tài khoản quản trị có tác động lớn nên cần kiểm soát người dùng, tài nguyên và thời hạn truy cập. PAM có thể hỗ trợ quản lý bí mật và phiên; phạm vi phụ thuộc giải pháp đã chọn.',
'Có bao nhiêu admin, tài khoản dịch vụ và nhà thầu? Hệ thống nào cần ghi phiên?',
'Phân loại tài khoản người dùng và tài khoản dịch vụ|Pilot tài sản lab và kiểm đường truy cập dự phòng|Thử cấp quyền tạm thời và thu hồi|Kiểm khả năng xem audit của người có thẩm quyền',
'Danh mục đặc quyền; ma trận duyệt; kết quả pilot và break-glass.', 'Không lưu mật khẩu thật trong kho tri thức hoặc ảnh chụp phiên demo.'),
('ZERO-TRUST','Zero Trust và truy cập theo tài nguyên','Kiến trúc bảo mật','zt',
'Zero Trust không mặc định tin cậy chỉ vì người dùng hoặc thiết bị ở mạng nội bộ. Quyết định truy cập phải xét danh tính, thiết bị và tài nguyên; không đồng nghĩa một sản phẩm duy nhất.',
'Ứng dụng nào cần truy cập từ xa? Thiết bị có được quản lý không? Có ứng dụng legacy?',
'Chọn một ứng dụng pilot không trọng yếu|Mô tả người dùng, thiết bị, chính sách và log|Thử truy cập đúng điều kiện và điều kiện bị từ chối|Đánh giá trải nghiệm cùng phương án quay lui',
'Sơ đồ luồng truy cập; ma trận điều kiện; kết quả pilot.', 'Không hứa thay toàn bộ VPN ngay khi chưa kiểm phụ thuộc ứng dụng.'),
('SEGMENT','Phân đoạn mạng và hạn chế lan truyền','Kiến trúc bảo mật','csf',
'Phân đoạn chia vùng theo mức tin cậy và nhu cầu giao tiếp. VLAN tạo phân tách logic; cần kiểm soát lưu lượng giữa vùng và quyền quản trị để giảm di chuyển ngang.',
'Mạng khách, camera, server và quản trị đang dùng chung? Ứng dụng cần cổng nào?',
'Vẽ sơ đồ vùng và luồng nghiệp vụ|Lập bảng nguồn/đích/dịch vụ/owner|Pilot rule trên lab và thử luồng hợp lệ|Kiểm luồng bị chặn, log và rollback trước mở rộng',
'Ma trận luồng; rule có owner; UAT từng ứng dụng.', 'Không đổi rule production dựa trên sơ đồ thiếu phụ thuộc DNS, AD hoặc backup.'),
('RANSOMWARE','Ransomware: phòng ngừa và phản ứng ban đầu','Ứng cứu sự cố','ransom',
'Ransomware có thể gây gián đoạn và đi kèm đánh cắp dữ liệu. Cần bảo vệ tài khoản, giảm bề mặt phơi lộ và giữ bản sao lưu tách biệt. Khi nghi nhiễm, phối hợp cô lập và giữ chứng cứ.',
'Máy nào bị ảnh hưởng? Mốc giờ phát hiện? Backup có tách tài khoản và kiểm restore chưa?',
'Báo đầu mối ứng cứu qua kênh tin cậy|Xác định hệ thống bị ảnh hưởng và cô lập theo quyền được cấp|Bảo toàn log, timeline và thông tin dấu hiệu|Kiểm phương án khôi phục sạch trong môi trường tách biệt',
'Timeline; danh sách máy; bằng chứng bảo toàn; báo cáo restore.', 'Không xóa log, tự chạy công cụ giải mã lạ hoặc hứa khôi phục theo một thời hạn chung.'),
('BACKUP-SEC','Backup bất biến, offline và kiểm khôi phục','Dữ liệu & khôi phục','ransom',
'Backup có ích khi bản sao còn nguyên vẹn và khôi phục được. CISA khuyến nghị bản sao offline, mã hóa và kiểm thử. Bất biến là một biện pháp bảo vệ bản sao; cần xét cấu hình và quyền quản trị.',
'RPO/RTO do ai xác nhận? Có bản sao độc lập? Khóa mã hóa và tài khoản backup được bảo vệ ra sao?',
'Chọn bộ dữ liệu lab đại diện|Thử khôi phục bằng tài khoản được cấp đúng quyền|Đo thời gian và so đối chiếu dữ liệu|Ghi thiếu sót về phụ thuộc, khóa và dung lượng',
'Restore report; mốc phục hồi; thời gian đo; checklist phụ thuộc.', 'Job backup xanh không đồng nghĩa đáp ứng RTO; không tự xóa bản sao để thử tính bất biến.'),
('IR','Quy trình ứng cứu sự cố và phân công','Ứng cứu sự cố','ir',
'NIST SP 800-61 Rev. 3 tích hợp ứng cứu sự cố với quản trị rủi ro theo CSF 2.0. Chuẩn bị, phát hiện, ứng phó, khôi phục và cải tiến cần phối hợp giữa kỹ thuật và nghiệp vụ.',
'Ai có quyền tuyên bố sự cố? Ai duyệt cô lập? Ai cập nhật khách hàng và ban lãnh đạo?',
'Tiếp nhận mô tả và đánh giá tác động|Giao điều phối, kỹ sư và người duyệt thay đổi|Lập timeline, nhiệm vụ, kênh liên lạc|Đánh giá khôi phục và tổ chức rút kinh nghiệm',
'RACI; incident ticket; timeline; biên bản lessons learned.', 'SLA phản hồi không phải thời gian điều tra hoặc khắc phục xong.'),
('EVIDENCE','Bảo toàn chứng cứ và timeline sự cố','Ứng cứu sự cố','ir',
'Chứng cứ cần giữ bối cảnh nguồn, thời gian và người xử lý. Thay đổi trên máy nghi nhiễm có thể làm mất thông tin; quy trình thu thập cần do người được phân công thực hiện.',
'Đồng hồ máy có đồng bộ? Log nằm đâu? Ai đã thao tác sau phát hiện?',
'Ghi thời điểm và múi giờ của từng dấu hiệu|Lưu bản gốc log theo quy trình được duyệt|Ghi người thu thập, vị trí lưu và kiểm tra toàn vẹn|Làm việc trên bản sao và ghi mọi bàn giao',
'Sổ bàn giao; hash bản thu thập; timeline có nguồn.', 'Không khẳng định giá trị pháp lý hoặc thời hạn thông báo từ mẫu kỹ thuật này.'),
('PHISHING','Phishing, BEC và xác minh yêu cầu chuyển tiền','Nhận thức ATTT','mfa',
'Phishing giả mạo thông điệp hoặc trang đăng nhập để lấy thông tin. BEC có thể lợi dụng tài khoản thư thật đã bị chiếm. MFA là một lớp bảo vệ; quy trình xác minh giao dịch vẫn cần thiết.',
'Có yêu cầu đổi tài khoản thanh toán gấp? Địa chỉ gửi và lịch sử trao đổi có bất thường?',
'Dừng thao tác chuyển tiền hoặc nhập thông tin từ thư nghi ngờ|Xác minh qua đầu mối đã biết từ trước|Báo ticket kèm header và mốc giờ, che dữ liệu không cần thiết|Nếu đã nhập thông tin, chuyển đội ứng cứu xử lý phiên và tài khoản',
'Phiếu báo thư; kết quả xác minh; hành động tài khoản.', 'Không dùng số điện thoại mới chỉ xuất hiện trong thư nghi giả mạo để xác minh.'),
('KEV','Ưu tiên lỗ hổng bằng KEV và mức phơi lộ','Quản lý lỗ hổng','kev',
'CISA KEV ghi nhận lỗ hổng đã bị khai thác thực tế. Đây là một đầu vào để ưu tiên xử lý cùng độ quan trọng tài sản, khả năng bị tiếp cận và biện pháp giảm thiểu.',
'Phiên bản nào đang chạy? Có public Internet? Có bản vá hoặc hướng dẫn hãng? Tài sản có owner?',
'Đối chiếu inventory với thông báo hãng và KEV có ngày cập nhật|Xác minh đúng sản phẩm/phiên bản và mức phơi lộ|Lập thứ tự xử lý dựa tác động và khai thác thực tế|Kiểm lại sau vá và ghi ngoại lệ có người duyệt',
'Bảng tài sản/CVE; nguồn có ngày; ticket vá; kết quả xác minh.', 'Không có danh sách CVE thời gian thực trong demo; không áp hạn pháp lý của cơ quan Mỹ cho khách Việt Nam.'),
('PATCH','Quản lý bản vá và kiểm thay đổi','Quản lý lỗ hổng','kev',
'Vá lỗi phải đi kèm kiểm tương thích và bằng chứng sau thay đổi. Khi chưa vá được, ghi biện pháp giảm thiểu, chủ sở hữu rủi ro và thời điểm xem xét lại.',
'Có HA, backup cấu hình và maintenance window? Ai kiểm UAT? Có bản vá phụ thuộc?',
'Xác nhận bản vá theo advisory đúng phiên bản|Thử trong lab hoặc nhóm pilot|Ghi rollback và duyệt change|Kiểm phiên bản, chức năng và dấu hiệu lỗi sau triển khai',
'Change record; UAT; log sau vá; danh sách ngoại lệ.', 'Không suy ra hệ thống an toàn chỉ từ thông báo cài bản vá thành công.'),
('SOC','SOC, SIEM, EDR và trách nhiệm vận hành','Giám sát & SOC','attack',
'SOC là năng lực con người và quy trình giám sát/ứng cứu. SIEM tập trung và tương quan log; EDR quan sát và hỗ trợ phản ứng trên endpoint. MITRE ATT&CK mô tả hành vi đối thủ để hỗ trợ thiết kế kịch bản phát hiện.',
'Nguồn log nào có sẵn? Ai trực và ai được cô lập máy? Cần theo dõi endpoint hay ứng dụng?',
'Chọn use case đăng nhập bất thường trong lab|Xác định log, trường cần có và người xử lý|Tạo sự kiện kiểm thử lành tính và kiểm cảnh báo|Diễn tập ticket, phân loại và bàn giao ca',
'Use-case sheet; sự kiện test; ticket; ma trận trách nhiệm.', 'Một dashboard hoặc license SIEM không tự tạo dịch vụ SOC 24/7.'),
('DETECTION','Use case phát hiện và điều chỉnh cảnh báo','Giám sát & SOC','attack',
'Phát hiện cần dữ liệu phù hợp, giả thuyết hành vi và khả năng điều tra. Gắn ATT&CK hỗ trợ mô tả phạm vi nhưng không chứng minh đã phát hiện đầy đủ kỹ thuật đó.',
'Cảnh báo đang nhiễu ở nguồn nào? Có phân biệt bảo trì và hành vi bất thường?',
'Viết mục tiêu và tín hiệu dự kiến cho một use case|Kiểm chất lượng trường thời gian, tài khoản, máy nguồn|Thử ca dương tính mô phỏng và ca hoạt động bình thường|Ghi false positive, điểm mù và điều kiện tuning',
'Rule version; test cases; kết quả precision mẫu; chủ sở hữu.', 'Không công bố tỷ lệ phát hiện tổng thể từ một bộ test nhỏ.'),
('LOGGING','Log bảo mật: thu thập và bảo vệ dữ liệu','Giám sát & SOC','log',
'Log ứng dụng bổ sung bối cảnh mà log hạ tầng có thể thiếu. Nên ghi ai làm gì, khi nào, ở đâu và kết quả; tránh ghi mật khẩu, token và dữ liệu nhạy cảm không cần thiết.',
'Log có request ID và múi giờ? Ai được đọc? Có lọc thông tin nhạy cảm?',
'Thiết kế schema cho đăng nhập và đổi quyền trong app demo|Gửi sự kiện test rồi đối chiếu trên nguồn và nơi nhận|Kiểm log không chứa token/mật khẩu|Thử mất kết nối nơi nhận và ghi cách phục hồi thu thập',
'Schema; mẫu log đã che; kiểm quyền đọc; báo cáo thất thoát.', 'Không tự đặt retention pháp lý hoặc ghi toàn bộ payload khách hàng.'),
('WEB','OWASP Top 10 và tư vấn bảo mật web','Web & API','web',
'OWASP Top 10:2025 là tài liệu nhận thức về các nhóm rủi ro ứng dụng web. Có thể dùng mở đầu trao đổi về phân quyền, cấu hình, chuỗi cung ứng và các biện pháp trong vòng đời phát triển.',
'Web xử lý loại dữ liệu nào? Ai phát triển? Có môi trường test và owner xử lý lỗi?',
'Lập sơ đồ web, API, đăng nhập và dữ liệu|Chọn các chức năng quan trọng để review|Xác định kiểm thử, sửa code và lớp bảo vệ bổ sung|Ghi scope và tiêu chí kiểm lại lỗi',
'Scope ứng dụng; backlog rủi ro; kết quả retest.', 'Top 10 không thay một tiêu chuẩn kiểm thử đầy đủ; WAF không tự sửa lỗi logic hoặc phân quyền.'),
('API','Bảo mật API và kiểm quyền trên đối tượng','Web & API','api',
'API có rủi ro phân quyền đối tượng, xác thực và quản lý tài nguyên. Mỗi yêu cầu phải được kiểm quyền phù hợp; biết hoặc đổi một ID không đồng nghĩa được quyền xem đối tượng.',
'API có nhiều tenant? Có tài khoản test từng vai trò? Endpoint cũ còn hoạt động?',
'Tạo hai tenant và dữ liệu giả lập riêng|Kiểm user chỉ đọc/sửa đối tượng được cấp|Kiểm endpoint quản trị bằng user thường|Đánh giá giới hạn tài nguyên và inventory API',
'Ma trận vai trò/endpoint; kết quả positive/negative test.', 'Chỉ kiểm môi trường và tài khoản được phép; WAF không thay kiểm quyền trong backend.'),
('SECRET','Quản lý secret, token và khóa ứng dụng','Dữ liệu & khôi phục','secret',
'Secret cần có owner, quyền truy cập, vòng đời và khả năng thu hồi. Tránh hardcode trong source hoặc đưa vào log; ưu tiên kho quản lý tập trung và danh tính workload phù hợp.',
'Secret đang nằm ở file, CI hay kho mã? Có biết ứng dụng nào dùng khi xoay khóa?',
'Lập inventory bằng tên và owner, không chép giá trị|Dùng secret giả trong lab để kiểm cấp quyền|Xoay khóa thử và xác minh ứng dụng vẫn hoạt động|Thu hồi khóa cũ rồi kiểm audit truy cập',
'Inventory metadata; rotation test; bằng chứng thu hồi.', 'Xóa secret khỏi commit mới không làm secret đã lộ an toàn trở lại.'),
('CONTAINER','Hardening container và kiểm image','Cloud & nền tảng','container',
'Container dùng chung một phần nền tảng host nên cần kiểm quyền và cấu hình. Tránh đặc quyền không cần thiết; quản lý image và cập nhật phụ thuộc phải đi cùng vận hành.',
'Ai tạo image? Có chạy root/privileged? Volume và secret được cấp thế nào?',
'Kiểm manifest và nguồn image trong lab|Thử quyền tối thiểu và filesystem chỉ đọc khi tương thích|Giới hạn tài nguyên, network và quyền mount|Quét image, xử lý phát hiện và kiểm lại ứng dụng',
'Danh sách image; kết quả scan; manifest đã review.', 'Không cung cấp lệnh hardening chung cho mọi workload hoặc coi container là VM cách ly tuyệt đối.'),
('AI-RAG','Prompt injection và bảo vệ AI nội bộ RAG','Bảo mật AI','ai',
'Prompt injection đưa chỉ dẫn không tin cậy vào câu hỏi hoặc tài liệu. Phân tách chỉ dẫn và dữ liệu giúp giảm rủi ro; kiểm quyền và quyền công cụ phải được thực thi ngoài LLM.',
'Tài liệu ai được tải lên? Quyền lọc trước truy xuất? Model có công cụ ghi dữ liệu hoặc gửi email?',
'Tạo tài liệu lab chứa yêu cầu bỏ qua quy tắc|Kiểm tài liệu chưa duyệt không được truy xuất|Dùng hai vai trò để kiểm nguồn ngoài quyền không vào prompt|Kiểm đầu ra và xác nhận không có hành động bên ngoài',
'Bộ câu hỏi adversarial; trace nguồn; kết quả ACL.', 'Không coi system prompt hoặc nhãn DEMO là ranh giới bảo mật đầy đủ.'),
('SUPPLIER','Đánh giá nhà cung cấp và trách nhiệm dữ liệu','Quản trị ATTT','csf',
'Dịch vụ thuê ngoài vẫn cần xác định trách nhiệm, quyền truy cập và phụ thuộc. Điều kiện hợp đồng, hỗ trợ và quy trình chấm dứt dịch vụ phải được đọc theo phạm vi cụ thể.',
'Dữ liệu lưu ở đâu? Nhà cung cấp có quyền gì? Ai xuất dữ liệu và thu hồi quyền khi kết thúc?',
'Lập ma trận trách nhiệm khách/nhà cung cấp|Yêu cầu bằng chứng kiểm soát phù hợp dữ liệu|Thử xuất dữ liệu mẫu và thu hồi tài khoản nhà thầu|Ghi đầu mối sự cố và kế hoạch thay thế',
'Bảng đánh giá; trách nhiệm; kết quả exit test.', 'Không tự tuyên bố chứng nhận hoặc tuân thủ pháp luật khi chưa có hồ sơ.'),
('TABLETOP','Diễn tập tabletop và báo cáo sau sự cố','Ứng cứu sự cố','ir',
'Tabletop là diễn tập thảo luận dựa tình huống để kiểm quyết định và phối hợp. Kết quả nên chỉ ra điểm cần cải tiến; không thay kiểm thử kỹ thuật hoặc phục hồi thực tế.',
'Ai tham gia? Muốn kiểm quyết định nào? Dừng diễn tập và phân biệt sự cố thật ra sao?',
'Thông báo rõ kịch bản giả lập máy sale nghi mã hóa|Lần lượt đưa tình huống mất truy cập, cảnh báo và yêu cầu khách|Ghi quyết định, người duyệt và khoảng trống thông tin|Chốt việc cải tiến kèm owner và lần kiểm lại',
'Kịch bản; biên bản quyết định; improvement backlog.', 'Không gửi cảnh báo giả ra khách thật hoặc vô hiệu hệ thống đang vận hành để diễn tập.')]

def build():
    docs=[]
    for key,title,category,ref,explanation,questions,workflow,evidence,limit in TOPICS:
        label,url=SOURCES[ref]
        for kind in ('GUIDE','LAB'):
            id=f'SEC-{kind}-{key}'
            if kind=='GUIDE':
                body=f'## 1. Hiểu đúng\n{explanation}\n\n## 2. Câu hỏi khảo sát đề xuất\n{questions}\n\n## 3. Bằng chứng nên yêu cầu\n{evidence}\n\n## 4. Giới hạn\n{limit}'
                roles=['sale','technical','admin'];name=title+' — kiến thức & tư vấn'
            else:
                body='## 1. Tình huống DEMO\nBài tập do nhóm biên soạn demo xây dựng cho công ty dưới 20 người; dùng tài khoản, tài sản và dữ liệu lab. Không phải quy trình hãng hoặc sự cố thật.\n\n## 2. Checklist đề xuất\n'+'\n'.join(f'{i+1}. {v}.' for i,v in enumerate(workflow.split('|')))+f'\n\n## 3. Hồ sơ đầu ra\n{evidence}\n\n## 4. Điều kiện áp dụng\n{limit}'
                roles=['technical','admin'];name=title+' — bài tập & checklist kỹ thuật'
            body+=f'\n\n## Nguồn và biên soạn\nTham khảo nền tảng: {label}. Bản diễn giải tiếng Việt và bài tập do demo biên soạn; không phải bản dịch tiêu chuẩn. Kiểm nguồn ngày {CHECKED}. Các câu hỏi, bước lab và đầu ra là đề xuất cho demo, không phải yêu cầu nguyên văn của nguồn.'
            docs.append(dict(id=id,title=name,category=category,body=body,roles=roles,customer=None,version='security-1.0',status='approved',valid_from=CHECKED,valid_to='2027-09-05',owner='Biên soạn tri thức ATTT demo',synthetic=kind=='LAB',knowledge_type='authored_exercise' if kind=='LAB' else 'editorial_reference',reviewed_at=CHECKED,topic=key,references=[dict(title=label,url=url,checked_at=CHECKED)]))
    return docs

def install():
    docs=build();data=ROOT/'data';export=data/'security_documents';export.mkdir(exist_ok=True)
    with sqlite3.connect(data/'demo.sqlite3') as db:
        for d in docs:
            old=db.execute('SELECT payload FROM docs WHERE id=?',(d['id'],)).fetchone()
            if old:
                existing=json.loads(old[0])
                if existing.get('version')!='security-1.0':continue
                d['status']=existing['status']
            db.execute('INSERT OR REPLACE INTO docs VALUES(?,?)',(d['id'],json.dumps(d,ensure_ascii=False)))
            refs='\n'.join(f'- [{r["title"]}]({r["url"]})' for r in d['references'])
            (export/(d['id']+'.md')).write_text('# '+d['title']+'\n\n'+d['body']+'\n\n'+refs,encoding='utf8')
    (data/'security_documents.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf8')
    (data/'security_manifest.json').write_text(json.dumps(dict(documents=len(docs),topics=len(TOPICS),reviewed_at=CHECKED,sources=SOURCES),ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(added_pack=len(docs),topics=len(TOPICS),references=len(SOURCES))))
if __name__=='__main__':install()
