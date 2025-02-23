![](../../resources/Hackathon-banner-2024.png)

# BAIby Monitor

The BAIby Monitor project is an open-source initiative aimed at developing a smart baby monitoring system that utilizes machine learning to detect a baby's cries and other activities, providing real-time notifications to parents or caregivers.

## Demo Video

For a visual demonstration of the BAIby Monitor project, watch this video:

[![BAIby Monitor Demo](https://img.youtube.com/vi/sXgL5g_A-u0/0.jpg)](https://youtu.be/sXgL5g_A-u0)


## Features

- **Cry Detection**: Employs machine learning algorithms to distinguish a baby's cries from other sounds, ensuring accurate alerts.
- **Real-Time Notifications**: Sends immediate alerts to connected devices when the baby cries or unusual activity is detected.
- **Activity Monitoring**: Tracks the baby's movements and sounds, offering insights into sleep patterns and behavior.
- **User-Friendly Interface**: Provides an intuitive dashboard for monitoring and configuring settings.

## Installation

 ## Setup Instructions
1. Follow README setup instructions of [CLIP application example](../../README.md)

2. **Navigate to the Project Directory**:

   ```bash
   cd hailo-CLIP/community_projects/baiby_monitor
   ```

3. **Install Dependencies**:

   Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up the Environment**:

   Create a `.env` file in the project directory and add necessary configuration variables as specified in `.env.example`.
   
   ** Telegram Bot Activation **:
   a. Find @bAIbyMonbot in the 'Telegram' App.
   b. Press the 'Start' Button.
   c. You are ready to receive messages to your Telegram.

6. **Run the Application**:

   ```bash
   python src/baiby_telegram.py
   ```

## Usage

- **Access the Dashboard**: Once the application is running, navigate to `http://localhost:5001` in your web browser to access the monitoring dashboard.
- **Configure Settings**: Use the dashboard to adjust sensitivity levels, notification preferences, and other settings.
- **Monitor Alerts**: Receive real-time notifications on the dashboard and connected devices when the system detects the baby crying or unusual activity.
