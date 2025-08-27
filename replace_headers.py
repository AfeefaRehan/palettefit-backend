# import os
# import re

# # === CONFIG: paste your exact header and footer HTML here ===
# NEW_HEADER = """
# <header>
#   <div class="logo">Palette and Fit</div>
#   <button id="menu-toggle" class="hamburger" aria-label="Toggle menu">☰</button>
#   <nav class="nav">
#     <a href="homepage1.html" class="active">Home</a>
#     <a href="men.html">Men</a>
#     <a href="women.html">Women</a>
#     <a href="aboutus.html">About us</a>
#     <a href="contactus.html">Contact us</a>
#     <a href="wishlist.html" class="wishlist">♡ Wishlist</a>
#     <a href="profile.html" class="profile-icon" title="Profile">
#       <svg viewBox="0 0 24 24" fill="none">
#         <circle cx="12" cy="8.5" r="4.2" fill="#fff" fill-opacity=".95"/>
#         <ellipse cx="12" cy="18" rx="7" ry="3.2" fill="#fff" fill-opacity=".38"/>
#       </svg>
#     </a>
#     <button class="btn darkmode-btn" id="darkModeToggle">
#       <span style="font-size:1.25em;">🌙</span> Dark Mode
#     </button>
#   </nav>
# </header>
# """.strip()

# NEW_FOOTER = """
# <footer>
#   <div class="footer-main">
#     <div class="footer-col">
#       <div style="font-weight:700; margin-bottom:0.7rem;">Need Help ?</div>
#       <div style="margin-bottom:0.4rem;">
#         <a href="contactus.html">Contact us</a>
#       </div>
#     </div>
#     <div class="footer-col">
#       <div style="font-weight:700; margin-bottom:0.7rem;">More Info</div>
#       <div style="margin-bottom:0.4rem;"><a href="aboutus.html">About us</a></div>
#       <div style="margin-bottom:0.4rem;"><a href="terms.html">Terms & Conditions</a></div>
#     </div>
#     <div class="footer-col">
#       <div style="font-weight:700; margin-bottom:0.7rem;">Location</div>
#       <div style="margin-bottom:0.4rem;">
#         <a href="mailto:support@PaletteandFit.com">support@PaletteandFit.com</a>
#       </div>
#       <div style="margin-bottom:0.4rem;">
#         <a href="https://www.google.com/maps?q=4162+Wayback+Lane,+Farmingdale,+New+York,+11735,+USA" target="_blank" rel="noopener noreferrer">
#           4162 Wayback Lane, Farmingdale
#         </a>
#       </div>
#       <div style="margin-bottom:0.4rem;">New York, 11735, USA</div>
#     </div>
#   </div>
#   <div style="text-align:center; margin-top:2.5rem; font-size:1.15rem;">
#     <strong>Palette and Fit</strong><br>
#     <span style="font-size:0.93rem; color:#bbb;">© 2025 Palette and Fit. All rights reserved.</span>
#   </div>
# </footer>
# """.strip()

# # Regex patterns
# HEADER_REGEX = re.compile(r"<header\b[^>]*>.*?</header>", re.IGNORECASE | re.DOTALL)
# FOOTER_REGEX = re.compile(r"<footer\b[^>]*>.*?</footer>", re.IGNORECASE | re.DOTALL)

# def replace_header_footer(filepath):
#     with open(filepath, 'r', encoding='utf-8') as f:
#         content = f.read()

#     new_content, h_count = HEADER_REGEX.subn(NEW_HEADER, content, count=1)
#     new_content, f_count = FOOTER_REGEX.subn(NEW_FOOTER, new_content, count=1)

#     if h_count or f_count:
#         with open(filepath, 'w', encoding='utf-8') as f:
#             f.write(new_content)
#         print(f"✅ Updated {os.path.relpath(filepath)} (headers: {h_count}, footers: {f_count})")
#     else:
#         print(f"⚠️  No header/footer found in {os.path.relpath(filepath)}")

# if __name__ == "__main__":
#     # Walk current directory
#     for root, _, files in os.walk('.'):
#         for name in files:
#             if name.lower().endswith('.html'):
#                 replace_header_footer(os.path.join(root, name))
