# 🎵 SN Fun Bot - Advanced K-pop Discord Bot

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3+-green.svg)](https://discordpy.readthedocs.io)
[![Gemini AI](https://img.shields.io/badge/Gemini-2.0%20Flash-orange.svg)](https://ai.google.dev)
[![Railway](https://img.shields.io/badge/Deploy-Railway-purple.svg)](https://railway.app)

Bot Discord AI canggih dengan **Gemini 2.0 Flash** untuk informasi K-pop real-time, deteksi cerdas member/grup, sistem caching Redis, dan monitoring komprehensif.

## ✨ Fitur Utama

### 🤖 **AI & Detection**
- **Gemini 2.0 Flash Integration**: AI terbaru Google dengan response super cepat
- **Category-Specific API Keys**: Load balancing otomatis untuk performa optimal
- **Smart K-pop Detection**: 5 kategori deteksi (MEMBER, GROUP, MEMBER_GROUP, OBROLAN, REKOMENDASI)
- **Multi-Model Fallback**: Fallback otomatis ke Gemini 1.5 Flash jika diperlukan
- **Context-Aware Responses**: Deteksi konteks percakapan untuk transisi yang natural

### 🔍 **Data & Performance**
- **Multi-Source Scraping**: Soompi, AllKPop, KProfiles, Wikipedia, Namu Wiki
- **Redis Caching**: Cache 24 jam dengan TTL otomatis
- **Rate Limiting**: Exponential backoff untuk API stability
- **Real-time Monitoring**: API usage tracking dan performance analytics

### 🛠️ **Production Ready**
- **Railway Optimized**: Build config dan logging khusus Railway
- **Hybrid Logging**: Emoji untuk Railway, ASCII untuk Windows
- **Error Handling**: Comprehensive fallback mechanisms
- **Scalable Architecture**: Modular design untuk easy maintenance

## 🏗️ Struktur Project

```
Sn Fun Bot/
├── 🚀 CORE SYSTEM
│   ├── main.py                    # Entry point dengan error handling
│   ├── bot_core.py                # Bot initialization + SmartKPopDetector
│   ├── ai_handler.py              # Gemini 2.0 Flash + category API keys
│   ├── commands.py                # Discord command handlers
│   ├── data_fetcher.py            # Multi-source scraping engine
│   ├── analytics.py               # Performance monitoring
│   └── logger.py                  # Hybrid logging (Railway/Windows)
│
├── 🔧 DETECTION ENGINE
│   └── patch/
│       ├── __init__.py            # Package marker
│       ├── smart_detector.py      # 5-category K-pop detection
│       └── stopwordlist.py        # Indonesian stopwords (70+ words)
│
├── 🚀 DEPLOYMENT
│   ├── requirements.txt           # Python dependencies
│   ├── Procfile                   # Railway deployment command
│   ├── runtime.txt                # Python 3.11.13
│   ├── railway.json               # Build optimization
│   └── .dockerignore              # Build speed optimization
│
├── 📊 DEVELOPMENT
│   ├── tests/                     # 22 test files (not for production)
│   ├── RAILWAY_ENV_SETUP.md       # Environment variables guide
│   ├── GITHUB_UPLOAD_LIST.md      # Deployment file priorities
│   └── INTEGRATION_STATUS.md      # Feature status tracking
│
└── 📁 LOCAL ONLY
    └── Database/                   # Local K-pop CSV (not uploaded)
        └── DATABASE_KPOP.csv
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (recommended for Railway)
- **Redis server** (auto-provided by Railway)
- **Discord Bot Token** ([Discord Developer Portal](https://discord.com/developers/applications))
- **Gemini API Key(s)** ([Google AI Studio](https://makersuite.google.com/app/apikey))

### 🔧 Local Development

1. **Clone repository:**
```bash
git clone https://github.com/yourusername/sn-fun-bot.git
cd "Sn Fun Bot"
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Environment variables (.env):**
```bash
# 🚨 WAJIB - Core Configuration
DISCORD_TOKEN=your_discord_bot_token_here
GEMINI_API_KEY_1=your_first_gemini_api_key
REDIS_URL=redis://localhost:6379
KPOP_CSV_ID=your_google_drive_csv_file_id

# ⚡ RECOMMENDED - Category-Specific Load Balancing
GEMINI_API_KEY_2=your_second_gemini_api_key
GEMINI_API_KEY_3=your_third_gemini_api_key

# 📊 OPTIONAL - Enhanced Features
STATUS_CHANNEL_ID=your_discord_channel_id_for_status
NEWS_API_KEY=your_newsapi_key
CSE_API_KEY_1=your_google_cse_key_1
CSE_ID_1=your_google_cse_id_1
```

4. **Run bot:**
```bash
python main.py
```

### 🚀 Railway Deployment (Recommended)

1. **Setup Railway:**
```bash
npm install -g @railway/cli
railway login
railway init
```

2. **Add environment variables:**
```bash
railway variables set DISCORD_TOKEN=your_token_here
railway variables set GEMINI_API_KEY_1=your_key_1
railway variables set GEMINI_API_KEY_2=your_key_2
railway variables set GEMINI_API_KEY_3=your_key_3
railway variables set KPOP_CSV_ID=your_csv_id
```

3. **Add Redis service:**
```bash
railway add redis
```

4. **Deploy:**
```bash
railway up
```

**✅ Bot akan otomatis start dengan Gemini 2.0 Flash + category load balancing!**

## 🎮 Commands & Usage

### `!sn <query>` - Main Command

Bot menggunakan **SmartKPopDetector** dengan 5 kategori otomatis:

#### 🎤 **K-pop Queries**
```bash
!sn IU                    # MEMBER: Info member IU
!sn NewJeans              # GROUP: Info grup NewJeans
!sn Jisoo BLACKPINK       # MEMBER_GROUP: Member + grup context
!sn rekomendasi lagu sad  # REKOMENDASI: AI recommendations
```

#### 💬 **Casual Conversation**
```bash
!sn siapa namamu?         # OBROLAN: Casual chat dengan AI
!sn hari ini hujan nih    # OBROLAN: General conversation
!sn apa kabar?            # OBROLAN: Friendly chat
```

#### 🔧 **Admin Commands**
```bash
!sn clearcache           # Clear Redis cache
!sn status               # Bot performance stats
```

### 🤖 **AI Response Examples**

**Member Query:**
> **IU (Lee Ji-eun)** 🎤
> 
> Lahir 16 Mei 1993, solo artist legendaris Korea! Dikenal dengan suara unik dan lagu hits seperti "Through the Night", "Palette". Aktif juga sebagai aktris di drama "Hotel Del Luna", "My Mister". Fun fact: Punya fandom UAENA yang super loyal! 💜

**Group Query:**
> **NewJeans** 🐰
> 
> Girl group rookie ADOR (HYBE) yang debut 2022! Member: Minji, Hanni, Danielle, Haerin, Hyein. Hits: "Attention", "Hype Boy", "Ditto". Konsep Y2K aesthetic yang fresh banget! Fandom: Bunnies 🥕

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Category Assignment |
|----------|-------------|----------|--------------------|
| `DISCORD_TOKEN` | Discord bot token | ✅ | - |
| `GEMINI_API_KEY_1` | Primary Gemini API key | ✅ | OBROLAN (casual chat) |
| `GEMINI_API_KEY_2` | Secondary Gemini API key | ⚡ | KPOP (K-pop info) |
| `GEMINI_API_KEY_3` | Tertiary Gemini API key | ⚡ | REKOMENDASI (recommendations) |
| `KPOP_CSV_ID` | Google Drive CSV ID | ✅ | - |
| `REDIS_URL` | Redis server URL | ✅ | - |
| `STATUS_CHANNEL_ID` | Discord status channel | ❌ | - |
| `NEWS_API_KEY` | NewsAPI key | ❌ | - |
| `CSE_API_KEY_1-3` | Google Custom Search keys | ❌ | - |
| `CSE_ID_1-3` | Google CSE IDs | ❌ | - |

### 🎯 **Category-Specific API Key Benefits:**
- **Load Balancing**: Requests distributed across multiple keys
- **Rate Limit Avoidance**: Each key has separate quota
- **High Availability**: Automatic fallback if one key fails
- **Optimal Performance**: Dedicated keys per query type

### 🔄 **Model Fallback Sequence:**
1. **gemini-2.0-flash-exp** (Primary - fastest)
2. **gemini-1.5-flash** (Fallback 1 - reliable)
3. **gemini-1.5-flash-8b** (Fallback 2 - lightweight)

### 📊 Data Sources & Scraping

| Source | Type | Content | Status |
|--------|------|---------|--------|
| **Soompi** | News | Latest K-pop news & updates | ✅ Active |
| **AllKPop** | News | Articles & entertainment news | ✅ Active |
| **KProfiles** | Database | Member profiles & group info | ✅ Active |
| **Wikipedia** | Encyclopedia | Comprehensive information | ✅ Active |
| **Namu Wiki** | Wiki | Korean wiki content | ✅ Active |
| **Naver** | Search | Korean search engine | ✅ Active |
| **NewsAPI** | Global News | International news (optional) | ⚡ Optional |
| **Google CSE** | Custom Search | Targeted search results (optional) | ⚡ Optional |
| **Local CSV** | Database | K-pop member/group database | ✅ Core |

### 🔍 **Smart Detection Algorithm:**
1. **Alias Check**: Exact match dengan known aliases
2. **Group Match**: Fuzzy matching dengan grup names
3. **Member Match**: Fuzzy matching dengan member names  
4. **Fuzzy Search**: Advanced similarity scoring
5. **AI Context**: Gemini AI untuk ambiguous cases

## 🧠 Advanced AI Features

### 🎯 **Smart Detection Engine**
- **5-Category Classification**: MEMBER, GROUP, MEMBER_GROUP, OBROLAN, REKOMENDASI
- **False Positive Prevention**: Length filter (≤2 chars) dengan exception list
- **Multiple Match Handling**: User interaction untuk nama ambiguous
- **Context Awareness**: Seamless transition antar kategori
- **Indonesian Stopwords**: 70+ kata untuk filter casual conversation
- **Exception List**: Support untuk nama valid seperti "IU", "CL", "GD", "KEY"

### 🤖 **Gemini 2.0 Flash Integration**
- **Ultra-Fast Responses**: 2-3x lebih cepat dari model sebelumnya
- **Enhanced Reasoning**: Better context understanding
- **Multilingual Support**: Optimal untuk queries bahasa Indonesia
- **Category-Specific Prompting**: Customized prompts per query type

### 📝 **Response Generation**

#### **Member Profiles:**
- Nama lengkap + stage name
- Tanggal lahir & zodiac
- Posisi dalam grup
- Social media & fun facts
- Recent activities & rumors
- Narrative style yang engaging

#### **Group Information:**
- Debut date & agency
- Member lineup & positions  
- Discography highlights
- Awards & achievements
- Fandom name & culture
- Current activities

#### **Recommendations:**
- Personalized suggestions
- Mood-based recommendations
- Similar artists/songs
- Trending content

### 🔄 **Error Handling & Fallback**
- **Multi-Model Fallback**: Automatic switching jika model gagal
- **Rate Limiting**: Exponential backoff untuk 429/503 errors
- **Graceful Degradation**: Fallback responses jika semua AI gagal
- **Retry Logic**: Smart retry dengan different API keys

## 📊 Monitoring & Analytics

### 🔍 **Real-Time Monitoring**
- **API Usage Tracking**: Per-category call counts
- **Response Time Metrics**: Performance analysis
- **Error Rate Monitoring**: Success/failure ratios
- **Cache Performance**: Hit/miss statistics
- **Load Balancing Analysis**: API key distribution

### 📈 **Performance Metrics**
```
🚀 API Performance:
├── Total Calls: 1,247
├── Success Rate: 98.2%
├── Avg Response: 1.2s
└── Cache Hit Rate: 76%

⚖️ Load Balancing:
├── OBROLAN (Key 1): 34%
├── KPOP (Key 2): 41% 
└── REKOMENDASI (Key 3): 25%
```

### 🎨 **Hybrid Logging System**
- **Railway**: Emoji-rich logs untuk visual clarity
- **Windows**: ASCII fallback untuk compatibility
- **Structured Logging**: JSON format untuk analytics
- **Error Tracking**: Comprehensive error categorization

### 📊 **Analytics Dashboard**
- Hourly usage statistics
- Category distribution analysis
- Performance trend tracking
- Error pattern identification
- Resource utilization monitoring

## 🚀 Production Deployment

### 🌟 **Railway (Recommended)**

**Why Railway?**
- ✅ Auto-scaling & zero-downtime deploys
- ✅ Built-in Redis service
- ✅ Environment variable management
- ✅ Real-time logs dengan emoji support
- ✅ Optimized untuk Python bots

**Deployment Steps:**
```bash
# 1. Setup Railway
npm install -g @railway/cli
railway login
railway init

# 2. Environment Variables
railway variables set DISCORD_TOKEN=your_token
railway variables set GEMINI_API_KEY_1=your_key_1
railway variables set GEMINI_API_KEY_2=your_key_2
railway variables set GEMINI_API_KEY_3=your_key_3
railway variables set KPOP_CSV_ID=your_csv_id

# 3. Add Redis
railway add redis

# 4. Deploy
railway up
```

### 🐳 **Docker Alternative**
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Exclude development files
RUN rm -rf tests/ Database/ __pycache__/

# Run bot
CMD ["python", "main.py"]
```

### ☁️ **Other Platforms**

**Heroku:**
```bash
git push heroku main
```

**DigitalOcean App Platform:**
```yaml
name: sn-fun-bot
services:
- name: bot
  source_dir: /
  github:
    repo: yourusername/sn-fun-bot
    branch: main
  run_command: python main.py
```

### 📋 **Pre-Deployment Checklist**
- ✅ Environment variables configured
- ✅ Redis service added
- ✅ Gemini API keys valid
- ✅ Discord bot permissions set
- ✅ CSV database accessible
- ✅ Build optimization files included

## 🤝 Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push branch: `git push origin feature/new-feature`
5. Submit Pull Request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Troubleshooting & Support

### 🔧 **Common Issues**

#### **Bot tidak start:**
```bash
# Check Railway logs
railway logs

# Verify environment variables
railway variables

# Check Python version
python --version  # Should be 3.11+
```

#### **AI tidak respond:**
- ✅ Verify `GEMINI_API_KEY_1` set correctly
- ✅ Check Gemini API quota di [Google AI Studio](https://makersuite.google.com)
- ✅ Test API key dengan curl:
```bash
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

#### **Redis connection errors:**
- ✅ Ensure Redis service added di Railway
- ✅ Check `REDIS_URL` variable set correctly
- ✅ Verify Redis service status

#### **Detection tidak akurat:**
- ✅ Update `DATABASE_KPOP.csv` dengan data terbaru
- ✅ Check `KPOP_CSV_ID` pointing ke correct Google Drive file
- ✅ Verify CSV format: columns `Name`, `Group`, `Stage Name`

### 📞 **Getting Help**

1. **Check Logs**: Railway dashboard → Logs tab
2. **Environment Variables**: Verify all required vars set
3. **API Status**: Check Gemini AI service status
4. **Redis Health**: Verify Redis service running
5. **CSV Access**: Test Google Drive CSV accessibility

### 🐛 **Bug Reports**

When reporting bugs, include:
- Error message lengkap
- Steps to reproduce
- Environment (Railway/local)
- Bot version
- Query yang menyebabkan error

### 💡 **Feature Requests**

Suggestions welcome untuk:
- New K-pop data sources
- Detection algorithm improvements
- Performance optimizations
- UI/UX enhancements

## 🔄 Version History

### **v2.0** - Gemini 2.0 Flash Era 🚀
- ✅ **Gemini 2.0 Flash Integration**: Ultra-fast AI responses
- ✅ **Category-Specific API Keys**: Load balancing optimization
- ✅ **Advanced Monitoring**: Real-time analytics dashboard
- ✅ **Railway Optimization**: Production-ready deployment
- ✅ **Hybrid Logging**: Railway + Windows compatibility

### **v1.5** - Smart Detection Revolution 🧠
- ✅ **5-Category Detection**: MEMBER, GROUP, MEMBER_GROUP, OBROLAN, REKOMENDASI
- ✅ **Context Awareness**: Seamless conversation transitions
- ✅ **False Positive Prevention**: Advanced filtering algorithms
- ✅ **Multiple Match Handling**: User interaction untuk ambiguous queries

### **v1.4** - Performance & Reliability 📊
- ✅ **Multi-Model Fallback**: Automatic model switching
- ✅ **Rate Limiting**: Exponential backoff implementation
- ✅ **Error Handling**: Comprehensive fallback mechanisms
- ✅ **Cache Optimization**: 24-hour TTL dengan Redis

### **v1.3** - Enhanced Caching 💾
- ✅ **Redis Integration**: Sub-second cached responses
- ✅ **Performance Optimization**: Response time improvements
- ✅ **Memory Management**: Efficient caching strategies

### **v1.2** - Modular Architecture 🏗️
- ✅ **Code Refactoring**: Separated concerns architecture
- ✅ **Patch System**: Modular detection engine
- ✅ **Logging System**: Structured logging implementation

### **v1.1** - Multi-Source Integration 🌐
- ✅ **Multiple Data Sources**: Soompi, AllKPop, KProfiles integration
- ✅ **Web Scraping**: Advanced scraping capabilities
- ✅ **API Integration**: NewsAPI, Google CSE support

### **v1.0** - Foundation 🎯
- ✅ **Basic K-pop Detection**: Core detection functionality
- ✅ **AI Responses**: Initial Gemini AI integration
- ✅ **Discord Commands**: Basic command handling

## 🎯 **Roadmap**

### **v2.1** - Coming Soon
- 🔄 **Voice Integration**: Voice command support
- 🔄 **Image Recognition**: K-pop image identification
- 🔄 **Playlist Generation**: Spotify integration
- 🔄 **Multi-Language**: English language support

---

Made with ❤️ for K-pop fans worldwide! 🌟
