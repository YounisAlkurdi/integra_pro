import sys

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # The file contains text that was UTF-8, but incorrectly interpreted as CP1252
    # and then saved again as UTF-8. We reverse this process.
    try:
        # Convert back to the original bytes (CP1252 interpretation)
        # Some characters might not be valid in CP1252 if they were originally something else,
        # but for typical mojibake, this works.
        fixed_content = content.encode('cp1252').decode('utf-8')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print("Successfully fixed encoding!")
    except Exception as e:
        print("Error during conversion:", e)
        # fallback manual replace
        replacements = {
            "Ã¢â€ â‚¬": "─",
            "Ã¢â‚¬â€ ": "— ",
            "Ã¢â€ Â": "↳",
            "ÃÅ¸Â³": "↻",
            "ÃÅ“â€œ": "✅",
            "Ã¢â€”Â": "●",
            "Ã°Å¸â€ºÂ¡Ã¯Â¸Â": "🛡️",
            "Ã°Å¸â€œÂ¡": "📡",
            "Ã°Å¸â€ Â": "🔍",
            "Ã°Å¸Å¡Â¨": "🚨",
            "Ã˜Â§Ã™â€žÃ˜Â¯Ã˜Â®Ã™Ë†Ã™â€ž Ã™â€¦Ã˜ÂªÃ˜Â§Ã˜Â­": "الدخول متاح",
            "Ã˜ÂªÃ˜Â­Ã˜Â¯Ã™Å Ã˜Â« Ã˜Â§Ã™â€žÃ˜ÂµÃ™Â Ã˜Â­Ã˜Â©": "تحديث الصفحة",
            "Ã˜Â§Ã™â€žÃ˜ÂºÃ˜Â±Ã™Â Ã˜Â© Ã™â€¦Ã™â€¦Ã˜ÂªÃ™â€žÃ˜Â¦Ã˜Â©": "الغرفة ممتلئة",
            "Ã™â€¦Ã˜Â­Ã˜Â§Ã™Ë†Ã™â€žÃ˜Â© Ã˜Â§Ã™â€žÃ˜Â¯Ã˜Â®Ã™Ë†Ã™â€ž Ã™â€¦Ã˜Â¬Ã˜Â¯Ã˜Â¯Ã˜Â§Ã™â€¹": "محاولة الدخول مجددا",
            "Ã˜Â§Ã™â€ Ã˜ÂªÃ™â€¡Ã˜Âª Ã˜ÂµÃ™â€žÃ˜Â§Ã˜Â­Ã™Å Ã˜ÂªÃ™â€¡": "انتهت صلاحيته",
            "Ã˜Â§Ã™â€ Ã˜ÂªÃ™â€¡Ã˜Âª Ã˜ÂµÃ™â€žÃ˜Â§Ã˜Â­Ã™Å Ã˜Â© Ã˜Â§Ã™â€žÃ˜Â±Ã˜Â§Ã˜Â¨Ã˜Â·": "انتهت صلاحية الرابط",
            "Ã˜Â§Ã™â€žÃ˜Â¹Ã™Ë†Ã˜Â¯Ã˜Â© Ã™â€žÃ™â€žÃ˜Â±Ã˜Â¦Ã™Å Ã˜Â³Ã™Å Ã˜Â©": "العودة للرئيسية",
            "Ã˜Â§Ã™â€žÃ™â€¦Ã™Ë†Ã˜Â¹Ã˜Â¯ Ã™â€žÃ™â€¦ Ã™Å Ã˜Â­Ã™â€  Ã˜Â¨Ã˜Â¹Ã˜Â¯. Ã™Å Ã™â€¦Ã™Æ’Ã™â€ Ã™Æ’ Ã˜Â§Ã™â€žÃ˜Â¯Ã˜Â®Ã™Ë†Ã™â€ž Ã™â€šÃ˜Â¨Ã™â€ž 5 Ã˜Â¯Ã™â€šÃ˜Â§Ã˜Â¦Ã™â€š (Ã™â€¦Ã˜Â¨Ã™â€šÃ™Å  ${minutes} Ã˜Â¯Ã™â€šÃ™Å Ã™â€šÃ˜Â©)": "الموعد لم يحن بعد. يمكنك الدخول قبل 5 دقائق (متبقي ${minutes} دقيقة)",
            "Ã™â€¦Ã˜ÂªÃ˜Â¨Ã™â€šÃ™Å  ${minutes} Ã˜Â¯Ã™â€šÃ™Å Ã™â€šÃ˜Â©": "متبقي ${minutes} دقيقة",
        }
        for k, v in replacements.items():
            content = content.replace(k, v)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Fallback replacement done!")

if __name__ == '__main__':
    fix_file('c:\\tist_integra\\frontend\\js\\pages\\integra-session.js')
