# SN Fun Bot - K-pop Discord Bot 🎵

Bot Discord AI yang cerdas untuk informasi K-pop dengan deteksi otomatis member dan grup, dilengkapi sistem caching dan multiple data sources.

## ✨ Fitur Utama

- **Deteksi K-pop Otomatis**: Mendeteksi nama member/grup K-pop dari pesan dengan akurasi tinggi
- **AI-Powered Responses**: Menggunakan Google Gemini AI untuk ringkasan informasi yang natural
- **Multiple Data Sources**: Scraping dari Soompi, AllKPop, KProfiles, Wikipedia, dan lainnya
- **Redis Caching**: Sistem cache untuk response yang lebih cepat
- **Modular Architecture**: Kode terorganisir dalam modul-modul terpisah

## 🏗️ Struktur Project

```
Sn Fun Bot/
├── main.py              # Entry point utama
├── bot_core.py          # Inisialisasi bot dan konfigurasi
├── ai_handler.py        # Handler untuk Google Gemini AI
├── data_fetcher.py      # Scraping dan API calls
├── commands.py          # Discord commands handler
├── logger.py            # Logging system
├── requirements.txt     # Dependencies
├── Procfile            # Heroku deployment
├── Database/           # K-pop database
│   └── DATABASE_KPOP.csv
└── patch/              # Detection modules
    ├── detect_kpop_patch.py
    └── stopwordlist.py
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Redis server
- Discord Bot Token
- Google Gemini API Key

### Installation

1. Clone repository:
```bash
git clone <repository-url>
cd "Sn Fun Bot"
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:
```bash
# Discord
DISCORD_TOKEN=your_discord_token

# AI
GEMINI_API_KEY=your_gemini_api_key

# Database
KPOP_CSV_ID=your_google_drive_csv_id

# Cache
REDIS_URL=redis://localhost:6379

# Optional APIs
NEWS_API_KEY=your_news_api_key
CSE_API_KEY_1=your_google_cse_key_1
CSE_ID_1=your_google_cse_id_1
```

4. Run bot:
```bash
python main.py
```

## 🎮 Commands

### `!sn <query>`
Command utama untuk berinteraksi dengan bot.

**Contoh penggunaan:**
- `!sn IU` - Info tentang member IU
- `!sn NewJeans` - Info tentang grup NewJeans  
- `!sn siapa namamu?` - Pertanyaan umum
- `!sn clearcache` - Hapus cache Redis

## 🔧 Konfigurasi

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_TOKEN` | Token Discord bot | ✅ |
| `GEMINI_API_KEY` | API key Google Gemini AI | ✅ |
| `KPOP_CSV_ID` | Google Drive CSV ID untuk database K-pop | ✅ |
| `REDIS_URL` | URL Redis server | ✅ |
| `NEWS_API_KEY` | API key NewsAPI | ❌ |
| `CSE_API_KEY_*` | Google Custom Search API keys | ❌ |
| `CSE_ID_*` | Google Custom Search Engine IDs | ❌ |

### Data Sources

Bot mengambil informasi dari:
- **Soompi**: Berita K-pop terbaru
- **AllKPop**: Artikel dan update
- **KProfiles**: Profile member dan grup
- **Wikipedia**: Informasi ensiklopedia
- **Namu Wiki**: Wiki Korea
- **Naver**: Search engine Korea
- **NewsAPI**: Berita global
- **Google CSE**: Custom search results

## 🧠 AI Features

### Smart Detection
- Deteksi otomatis nama K-pop dari teks casual
- Filter false positive untuk kata pendek
- Support multiple matches untuk nama ambiguous
- Exception handling untuk nama valid seperti "IU", "CL"

### Response Generation
- **Member Profile**: Nama, ultah, social media, fun facts, rumors
- **Group Info**: Debut, member, discography, prestasi, fandom
- **Natural Language**: Response dalam bahasa Indonesia yang santai dan fun

## 📊 Logging & Monitoring

Bot dilengkapi sistem logging komprehensif:
- CSV load status
- Command usage tracking  
- Cache hit/miss statistics
- Error handling dan debugging

## 🚀 Deployment

### Heroku
```bash
git add .
git commit -m "Deploy bot"
git push heroku main
```

### Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## 🤝 Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push branch: `git push origin feature/new-feature`
5. Submit Pull Request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

Jika mengalami masalah:
1. Check logs untuk error messages
2. Pastikan semua environment variables sudah diset
3. Verify Redis server berjalan
4. Test API keys masih valid

## 🔄 Updates

- **v1.0**: Basic K-pop detection dan AI responses
- **v1.1**: Multiple data sources integration
- **v1.2**: Modular architecture refactor
- **v1.3**: Enhanced caching dan performance optimization

---

Made with ❤️ for K-pop fans worldwide! 🌟
