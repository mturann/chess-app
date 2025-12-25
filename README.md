# ♟️ Chess Analytics Hub

A comprehensive Streamlit-based chess analytics platform that helps players improve their game through data-driven insights, AI coaching, and machine learning predictions.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Features

### 📊 Analytics & Visualization
- **Profile Analysis** - Comprehensive player statistics and performance metrics
- **Rating History** - Interactive rating charts with trends, milestones, and forecasts
- **Time Management** - Clock usage patterns, time trouble detection, phase analysis
- **Opening Repertoire** - Opening performance stats, win rates, and recommendations

### 🤖 AI-Powered Features
- **Chess Coach** - AI coaching powered by Groq API with personalized advice
- **Rating Prediction** - ML-based rating forecast using Lasso regression
- **Win Probability** - Real-time win probability prediction with LightGBM

### 🎮 Live Features
- **Ongoing Games** - Track live games with real-time updates
- **Top Players** - Leaderboards and top player comparisons

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **ML/AI:** Scikit-learn, LightGBM, XGBoost
- **Visualization:** Plotly, Matplotlib, Seaborn
- **API:** Lichess API, Groq API
- **Data:** Pandas, NumPy

## 🚀 Quick Start
```bash
# Clone the repository
git clone https://github.com/yourusername/chess-app.git
cd chess-app

# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional, for AI features)
export GROQ_API_KEY=your_groq_api_key

# Run the app
streamlit run About.py
```

## 🔑 API Keys

| Feature | API Required |
|---------|--------------|
| Basic features | None (uses public Lichess API) |
| AI Chess Coach | [Groq API Key](https://console.groq.com/) |

## 📝 License

MIT License - feel free to use this project for learning and development.

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

---

<p align="center">
  Made with ❤️ for chess players
</p>
