CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  phone TEXT,
  name TEXT,
  age INT,
  gender TEXT,
  skin_tone TEXT,
  weight INT,
  body_length INT,
  upper_width INT,
  lower_width INT,
  reset_token TEXT,
  last_recommendation TEXT,
  best_color TEXT,
  worst_color TEXT,
  light_tones_percent INT,
  dark_tones_percent INT,
  western_percent INT,
  eastern_percent INT,
  personalized_analysis TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  image_url TEXT,
  gender TEXT,
  category TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wishlist (
  id SERIAL PRIMARY KEY,
  user_email TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
  product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_email, product_id)
);

CREATE TABLE IF NOT EXISTS chatbot_logs (
  id SERIAL PRIMARY KEY,
  user_email TEXT,
  question TEXT,
  bot_response TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contact_messages (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
