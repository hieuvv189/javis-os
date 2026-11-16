---
bump: minor
title: Messenger comments can get one private reply per comment
---
## vi
### Thêm mới
- **Bình luận Fanpage có thể được nhắn riêng.** Chế độ bình luận mới "nhắn riêng" theo từng Trang: bot gửi người bình luận đúng một tin Messenger riêng bám câu hỏi của họ thay vì trả lời công khai, không nhắn tiếp khi khách chưa trả lời, không gửi trùng khi Meta gửi lại webhook hay khi khởi động lại, và ghi rõ lỗi khi Meta từ chối (bình luận quá 7 ngày). Các Trang khác giữ nguyên chế độ cũ.

## en
### Added
- **Page comments can get a private reply.** A new per-Page comment mode "private": the bot sends the commenter exactly one private Messenger message about what they asked instead of a public reply, never follows up before they answer, never sends twice on a webhook retry or after a restart, and records Meta's refusal (comment older than 7 days) as a failure. Other Pages keep their mode.
