import google.generativeai as genai

try:
    genai.configure(api_key="AIzaSyDRsD4TZHvfbiE8RHjkJv_18Z4dbuoc-6Y")
    models = genai.list_models()
    print("MODELS OUTPUT:")
    for m in models:
        print(m)
except Exception as e:
    print("ERROR:", e)
