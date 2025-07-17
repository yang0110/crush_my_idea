conda create -n shit_env python=3.10 -y 
conda activate shit_env
pip install tavily-python 
pip install requests beautifulsoup4 
pip install markdownify 
pip install selenium webdriver_manager
# For Chrome, download ChromeDriver from https://googlechromelabs.github.io/chrome-for-testing/
# Or use webdriver_manager to handle it automatically (recommended)
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt --fix-broken install
sudo dpkg -i google-chrome-stable_current_amd64.deb
google-chrome --version
pip install playwright
playwright install  # This downloads browser binaries (Chromium, Firefox, WebKit)