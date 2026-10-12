import html
import re
import io
import json
import sqlite3
from datetime import datetime
import discord

def format_file_size(size_bytes):
    if not size_bytes or size_bytes == 0:
        return "Unknown size"
    size_bytes = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def parse_discord_markdown(text):
    if not text:
        return ""
    
    # 1. Escape HTML for security (XSS prevention)
    escaped = html.escape(text)
    
    # 2. Code blocks (```lang\ncode```)
    def re_codeblock(m):
        lang = m.group(1) or ""
        code = m.group(2)
        lang_label = f'<div class="code-lang">{html.escape(lang)}</div>' if lang else ''
        return f'<div class="codeblock">{lang_label}<pre><code>{code}</code></pre></div>'
    
    escaped = re.sub(r'```(?:([a-zA-Z0-9_+-]+)\n)?([\s\S]*?)```', re_codeblock, escaped)
    
    # 3. Inline code (`code`)
    escaped = re.sub(r'`([^`\n]+)`', r'<code class="inline-code">\1</code>', escaped)
    
    # 4. Bold (**text**)
    escaped = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', escaped)
    
    # 5. Italic (*text* or _text_)
    escaped = re.sub(r'\*(.*?)\*', r'<em>\1</em>', escaped)
    escaped = re.sub(r'_(.*?)_', r'<em>\1</em>', escaped)
    
    # 6. Underline (__text__)
    escaped = re.sub(r'__(.*?)__', r'<u>\1</u>', escaped)
    
    # 7. Strikethrough (~~text~~)
    escaped = re.sub(r'~~(.*?)~~', r'<del>\1</del>', escaped)
    
    # 8. Spoilers (||text||)
    escaped = re.sub(r'\|\|(.*?)\|\|', r'<span class="spoiler" onclick="this.classList.toggle(\'spoiler-revealed\')">\1</span>', escaped)
    
    # 9. Block Quotes (> text)
    lines = escaped.split('\n')
    processed_lines = []
    in_quote = False
    quote_acc = []
    
    for line in lines:
        if line.startswith('&gt; '):
            quote_acc.append(line[5:])
            in_quote = True
        elif line.startswith('&gt;'):
            quote_acc.append(line[4:])
            in_quote = True
        else:
            if in_quote:
                processed_lines.append(f'<blockquote class="quote">{"<br>".join(quote_acc)}</blockquote>')
                quote_acc = []
                in_quote = False
            processed_lines.append(line)
            
    if in_quote:
        processed_lines.append(f'<blockquote class="quote">{"<br>".join(quote_acc)}</blockquote>')
        
    escaped = "\n".join(processed_lines)
    
    # 10. Custom Emojis (<:name:id> and <a:name:id>)
    escaped = re.sub(r'&lt;a:([a-zA-Z0-9_]+):(\d+)&gt;', r'<img class="emoji" src="https://cdn.discordapp.com/emojis/\2.gif?v=1" alt=":\1:" title=":\1:">', escaped)
    escaped = re.sub(r'&lt;:([a-zA-Z0-9_]+):(\d+)&gt;', r'<img class="emoji" src="https://cdn.discordapp.com/emojis/\2.png?v=1" alt=":\1:" title=":\1:">', escaped)
    
    # 11. Mentions (@everyone, @here, <@id>, <#id>, <@&id>)
    escaped = re.sub(r'@everyone', r'<span class="mention everyone-mention">@everyone</span>', escaped)
    escaped = re.sub(r'@here', r'<span class="mention everyone-mention">@here</span>', escaped)
    escaped = re.sub(r'&lt;@!?(\d+)&gt;', r'<span class="mention">@\1</span>', escaped)
    escaped = re.sub(r'&lt;@&amp;(\d+)&gt;', r'<span class="mention role-mention">@Role</span>', escaped)
    escaped = re.sub(r'&lt;#(\d+)&gt;', r'<span class="mention channel-mention">#Channel</span>', escaped)
    
    # 12. Auto Linkification (URLs)
    escaped = re.sub(r'(https?://[^\s<]+)', r'<a href="\1" target="_blank" rel="noopener noreferrer" class="chat-link">\1</a>', escaped)
    
    # Replace remaining newlines with <br> inside regular text
    escaped = escaped.replace('\n', '<br>')
    return escaped

def render_attachment_item(attach):
    url = html.escape(attach.url)
    fname = html.escape(attach.filename)
    fsize = format_file_size(getattr(attach, 'size', 0))
    c_type = (getattr(attach, 'content_type', '') or "").lower()
    
    # 1. Images (.png, .jpg, .jpeg, .webp)
    if c_type.startswith('image/') and not fname.endswith('.gif'):
        return f'''
        <div class="attachment-box image-attachment">
            <div class="attachment-meta">📷 <strong>{fname}</strong> ({fsize})</div>
            <a href="{url}" target="_blank" rel="noopener noreferrer" class="img-preview-link">
                <img src="{url}" alt="{fname}" loading="lazy" class="attachment-img">
            </a>
            <div class="attachment-actions"><a href="{url}" target="_blank" rel="noopener noreferrer" class="open-link">Open Original</a></div>
        </div>
        '''
    # 2. GIFs (.gif)
    elif fname.endswith('.gif') or c_type == 'image/gif':
        return f'''
        <div class="attachment-box gif-attachment">
            <div class="attachment-meta">🎞️ <strong>{fname}</strong> ({fsize})</div>
            <a href="{url}" target="_blank" rel="noopener noreferrer">
                <img src="{url}" alt="{fname}" loading="lazy" class="attachment-img">
            </a>
            <div class="attachment-actions"><a href="{url}" target="_blank" rel="noopener noreferrer" class="open-link">Open GIF</a></div>
        </div>
        '''
    # 3. Videos (.mp4, .webm, .mov, .m4v)
    elif c_type.startswith('video/') or any(fname.endswith(ext) for ext in ['.mp4', '.webm', '.mov', '.m4v']):
        return f'''
        <div class="attachment-box video-attachment">
            <div class="attachment-meta">🎥 <strong>{fname}</strong> ({fsize})</div>
            <video controls preload="metadata" class="attachment-video">
                <source src="{url}">
                Your browser does not support HTML5 video playback.
            </video>
            <div class="attachment-actions"><a href="{url}" target="_blank" rel="noopener noreferrer" class="open-link">Open Video</a></div>
        </div>
        '''
    # 4. Audio (.mp3, .wav, .ogg, .m4a)
    elif c_type.startswith('audio/') or any(fname.endswith(ext) for ext in ['.mp3', '.wav', '.ogg', '.m4a', '.flac']):
        return f'''
        <div class="attachment-box audio-attachment">
            <div class="attachment-meta">🎵 <strong>{fname}</strong> ({fsize})</div>
            <audio controls class="attachment-audio">
                <source src="{url}">
                Your browser does not support HTML5 audio playback.
            </audio>
            <div class="attachment-actions"><a href="{url}" target="_blank" rel="noopener noreferrer" class="open-link">Download Audio</a></div>
        </div>
        '''
    # 5. Generic Files (.pdf, .zip, .docx, .xlsx, .txt, etc.)
    else:
        return f'''
        <div class="attachment-box file-attachment">
            <div class="file-icon">📎</div>
            <div class="file-details">
                <div class="file-name">{fname}</div>
                <div class="file-size">{fsize}</div>
            </div>
            <a href="{url}" target="_blank" rel="noopener noreferrer" class="file-download-btn">Open Attachment</a>
        </div>
        '''

def render_embed_item(embed):
    border_color = f"#{embed.color.value:06x}" if (embed.color and embed.color.value) else "#5865f2"
    
    author_html = ""
    if embed.author:
        a_icon = f'<img src="{html.escape(embed.author.icon_url)}" class="eb-author-icon">' if embed.author.icon_url else ''
        a_name = html.escape(embed.author.name or "")
        author_html = f'<div class="eb-author">{a_icon}<span>{a_name}</span></div>'
        
    title_html = ""
    if embed.title:
        t_text = html.escape(embed.title)
        if embed.url:
            title_html = f'<div class="eb-title"><a href="{html.escape(embed.url)}" target="_blank" rel="noopener noreferrer">{t_text}</a></div>'
        else:
            title_html = f'<div class="eb-title">{t_text}</div>'
            
    desc_html = ""
    if embed.description:
        desc_html = f'<div class="eb-desc">{parse_discord_markdown(embed.description)}</div>'
        
    fields_html = ""
    if embed.fields:
        f_items = ""
        for field in embed.fields:
            fn = html.escape(field.name or "")
            fv = parse_discord_markdown(field.value or "")
            f_items += f'<div class="eb-field"><div class="eb-field-name">{fn}</div><div class="eb-field-value">{fv}</div></div>'
        fields_html = f'<div class="eb-fields">{f_items}</div>'
        
    thumb_html = ""
    if embed.thumbnail and embed.thumbnail.url:
        thumb_html = f'<img src="{html.escape(embed.thumbnail.url)}" class="eb-thumbnail" alt="thumbnail">'
        
    image_html = ""
    if embed.image and embed.image.url:
        image_html = f'<div class="eb-image-wrap"><img src="{html.escape(embed.image.url)}" class="eb-image" alt="embed image"></div>'
        
    footer_html = ""
    if embed.footer or embed.timestamp:
        ft_icon = f'<img src="{html.escape(embed.footer.icon_url)}" class="eb-footer-icon">' if (embed.footer and embed.footer.icon_url) else ''
        ft_text = html.escape(embed.footer.text) if (embed.footer and embed.footer.text) else ''
        ts_text = embed.timestamp.strftime('%m/%d/%Y, %I:%M:%S %p') if embed.timestamp else ''
        separator = " • " if (ft_text and ts_text) else ""
        footer_html = f'<div class="eb-footer">{ft_icon}<span>{ft_text}{separator}{ts_text}</span></div>'

    # Action buttons preview if embed is welcome panel
    action_btns_html = ""
    if embed.title and ("Ticket Opened" in embed.title or "Create a Support" in embed.title or "Store" in embed.title):
        action_btns_html = '''
        <div class="embed-actions-row">
            <button class="btn-preview btn-preview-danger">🔒 Close Ticket</button>
            <button class="btn-preview btn-preview-secondary">🛈 Claim Ticket</button>
        </div>
        '''

    return f'''
    <div class="embed-box" style="border-left-color: {border_color};">
        <div class="eb-inner">
            {thumb_html}
            {author_html}
            {title_html}
            {desc_html}
            {fields_html}
            {image_html}
            {footer_html}
            {action_btns_html}
        </div>
    </div>
    '''

async def generate_full_html_transcript(channel, ticket_info, closer_user=None, close_reason="No reason provided", transcript_uuid=None):
    guild = channel.guild
    server_name = html.escape(guild.name) if guild else "Veyra"
    server_icon = html.escape(guild.icon.url) if (guild and guild.icon) else "https://cdn.discordapp.com/embed/avatars/0.png"
    channel_name = html.escape(channel.name)
    
    # Fetch ALL messages chronologically
    raw_messages = []
    async for msg in channel.history(limit=None, oldest_first=True):
        raw_messages.append(msg)
        
    total_messages_count = len(raw_messages)
    total_attachments_count = sum(len(msg.attachments) for msg in raw_messages)
    
    created_time_str = channel.created_at.strftime('%m/%d/%Y, %I:%M:%S %p') if channel.created_at else datetime.utcnow().strftime('%m/%d/%Y, %I:%M:%S %p')
    generation_time_str = datetime.utcnow().strftime('%m/%d/%Y, %I:%M:%S %p')
    
    closer_name = html.escape(closer_user.display_name) if (closer_user and hasattr(closer_user, 'display_name')) else "VEYRA Staff"
    closer_avatar = html.escape(closer_user.display_avatar.url) if (closer_user and hasattr(closer_user, 'display_avatar')) else "https://cdn.discordapp.com/embed/avatars/0.png"

    # Build chat messages HTML with date separators
    chat_html = ""
    last_date_str = None
    
    for msg in raw_messages:
        msg_date_str = msg.created_at.strftime('%m/%d/%Y, %I:%M:%S %p')
        if not last_date_str:
            chat_html += f'<div class="date-header-separator">{msg_date_str}</div>'
            last_date_str = msg_date_str
            
        # Reply preview
        reply_html = ""
        if msg.reference and msg.reference.message_id:
            ref_msg = next((m for m in raw_messages if m.id == msg.reference.message_id), None)
            if ref_msg:
                r_avatar = html.escape(ref_msg.author.display_avatar.url)
                r_author = html.escape(ref_msg.author.display_name)
                r_text = html.escape(ref_msg.clean_content[:120]) if ref_msg.clean_content else "Attachment / Embed"
                reply_html = f'''
                <div class="reply-bar">
                    <span style="color:var(--text-muted)">↳</span>
                    <img src="{r_avatar}" class="reply-avatar">
                    <span class="reply-author">{r_author}</span>
                    <span class="reply-snippet">"{r_text}"</span>
                </div>
                '''
                
        # Author details
        a_avatar = html.escape(msg.author.display_avatar.url)
        a_name = html.escape(msg.author.display_name)
        
        # Check if staff or bot
        b_tag = ''
        if msg.author.bot:
            b_tag = '<span class="bot-badge">BOT</span>'
        
        time_str = msg.created_at.strftime('%m/%d/%Y, %I:%M:%S %p')
        edited_str = '<span class="edited-tag">(edited)</span>' if msg.edited_at else ''
        
        # Message content
        msg_body = parse_discord_markdown(msg.content) if msg.content else ""

        # Attachments
        attach_html = ""
        if msg.attachments:
            items = "".join([render_attachment_item(att) for att in msg.attachments])
            attach_html = f'<div class="attachments-wrap">{items}</div>'
            
        # Embeds
        embeds_html = ""
        if msg.embeds:
            e_items = "".join([render_embed_item(emb) for emb in msg.embeds])
            embeds_html = f'<div class="embeds-wrap">{e_items}</div>'

        chat_html += f'''
        <div class="msg-block" data-message-id="{msg.id}">
            <img src="{a_avatar}" class="author-avatar" alt="avatar">
            <div class="msg-right">
                {reply_html}
                <div class="msg-meta">
                    <span class="author-name">{a_name}</span>{b_tag}
                    <span class="msg-timestamp">{time_str}</span>{edited_str}
                </div>
                {f'<div class="msg-text">{msg_body}</div>' if msg_body else ''}
                {attach_html}
                {embeds_html}
            </div>
        </div>
        '''

    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{server_name} - Transcript</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{
            --bg-primary: #313338;
            --bg-secondary: #2b2d31;
            --bg-tertiary: #1e1f22;
            --text-normal: #dbdee1;
            --text-muted: #94a3b8;
            --text-white: #ffffff;
            --accent-brand: #5865f2;
            --accent-green: #23a55a;
            --border-subtle: rgba(255, 255, 255, 0.06);
        }}
        * {{ box-sizing: border-box; }}
        body {{
            background-color: var(--bg-primary);
            color: var(--text-normal);
            font-family: 'gg sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
        }}
        /* Top Navigation Bar */
        .top-nav-bar {{
            background: #1e1f22;
            height: 56px;
            padding: 0 24px;
            display: flex;
            align-items: center;
            border-bottom: 1px solid var(--border-subtle);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .top-nav-brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .top-nav-icon {{
            width: 32px;
            height: 32px;
            border-radius: 50%;
            object-fit: cover;
        }}
        .top-nav-title {{
            font-size: 1.1rem;
            font-weight: 800;
            color: var(--text-white);
        }}
        .transcript-main {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 24px 16px 40px;
        }}
        .date-header-separator {{
            text-align: center;
            color: var(--text-muted);
            font-size: 0.78rem;
            font-weight: 600;
            margin: 20px 0 24px;
        }}
        /* Message Block */
        .msg-block {{
            display: flex;
            gap: 16px;
            margin-bottom: 20px;
            min-width: 0;
        }}
        .author-avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            object-fit: cover;
            flex-shrink: 0;
            background: var(--accent-brand);
        }}
        .msg-right {{
            flex: 1;
            min-width: 0;
        }}
        .reply-bar {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.78rem;
            color: var(--text-muted);
            margin-bottom: 6px;
        }}
        .reply-avatar {{ width: 16px; height: 16px; border-radius: 50%; }}
        .reply-author {{ font-weight: 700; color: var(--text-white); }}
        .reply-snippet {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 400px; }}
        .msg-meta {{
            display: flex;
            align-items: baseline;
            gap: 8px;
            margin-bottom: 4px;
        }}
        .author-name {{
            font-weight: 700;
            color: var(--text-white);
            font-size: 0.95rem;
        }}
        .bot-badge {{
            background: var(--accent-brand);
            color: #fff;
            font-size: 0.6rem;
            font-weight: 800;
            padding: 1px 5px;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        .msg-timestamp {{
            font-size: 0.75rem;
            color: var(--text-muted);
        }}
        .edited-tag {{
            font-size: 0.68rem;
            color: var(--text-muted);
            margin-left: 4px;
        }}
        .msg-text {{
            font-size: 0.92rem;
            line-height: 1.5;
            color: var(--text-normal);
            overflow-wrap: anywhere;
        }}
        /* Attachments & Embeds */
        .attachments-wrap, .embeds-wrap {{ margin-top: 10px; display: flex; flex-direction: column; gap: 10px; }}
        .attachment-box {{ background: var(--bg-tertiary); border-radius: 8px; border: 1px solid var(--border-subtle); padding: 12px; max-width: 520px; }}
        .attachment-meta {{ font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }}
        .attachment-img {{ max-width: 100%; max-height: 400px; height: auto; border-radius: 6px; display: block; }}
        .attachment-video {{ max-width: 100%; border-radius: 6px; }}
        .attachment-audio {{ width: 100%; }}
        .file-attachment {{ display: flex; align-items: center; gap: 14px; }}
        .file-icon {{ font-size: 1.8rem; color: var(--accent-brand); }}
        .file-details {{ flex: 1; min-width: 0; }}
        .file-name {{ font-weight: 700; color: var(--text-white); font-size: 0.88rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .file-size {{ font-size: 0.75rem; color: var(--text-muted); }}
        .file-download-btn, .open-link {{ background: rgba(88, 101, 242, 0.15); color: #5865f2; border: 1px solid rgba(88, 101, 242, 0.3); padding: 6px 14px; border-radius: 4px; text-decoration: none; font-size: 0.78rem; font-weight: 700; transition: all 0.2s ease; }}
        .file-download-btn:hover, .open-link:hover {{ background: var(--accent-brand); color: #fff; }}
        
        .embed-box {{ background: var(--bg-tertiary); border-radius: 6px; border-left: 4px solid var(--accent-brand); padding: 14px 18px; max-width: 520px; }}
        .eb-author {{ display: flex; align-items: center; gap: 8px; font-size: 0.8rem; font-weight: 700; color: var(--text-white); margin-bottom: 8px; }}
        .eb-author-icon {{ width: 20px; height: 20px; border-radius: 50%; }}
        .eb-title {{ font-size: 0.95rem; font-weight: 700; color: var(--text-white); margin-bottom: 6px; }}
        .eb-title a {{ color: #00aff4; text-decoration: none; }}
        .eb-desc {{ font-size: 0.85rem; line-height: 1.4; color: var(--text-normal); margin-bottom: 10px; }}
        .eb-fields {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-top: 10px; }}
        .eb-field-name {{ font-size: 0.78rem; font-weight: 700; color: var(--text-muted); margin-bottom: 2px; }}
        .eb-field-value {{ font-size: 0.82rem; color: var(--text-normal); }}
        .eb-thumbnail {{ float: right; max-width: 80px; max-height: 80px; border-radius: 6px; margin-left: 12px; }}
        .eb-image {{ max-width: 100%; border-radius: 6px; margin-top: 10px; }}
        .eb-footer {{ margin-top: 10px; font-size: 0.72rem; color: var(--text-muted); display: flex; align-items: center; gap: 6px; }}
        .eb-footer-icon {{ width: 16px; height: 16px; border-radius: 50%; }}

        /* Button elements preview inside embed */
        .embed-actions-row {{ display: flex; gap: 10px; margin-top: 12px; flex-wrap: wrap; }}
        .btn-preview {{ border: none; padding: 7px 16px; border-radius: 4px; font-size: 0.82rem; font-weight: 700; color: #fff; cursor: default; display: inline-flex; align-items: center; gap: 6px; }}
        .btn-preview-danger {{ background: #da373c; }}
        .btn-preview-secondary {{ background: #4e5058; }}

        /* Markdown styling */
        .inline-code {{ background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 0.85rem; }}
        .codeblock {{ background: #111214; border-radius: 6px; border: 1px solid var(--border-subtle); margin-top: 8px; overflow: hidden; }}
        .code-lang {{ background: rgba(255,255,255,0.05); color: var(--text-muted); font-size: 0.7rem; padding: 4px 10px; font-family: monospace; text-transform: uppercase; }}
        .codeblock pre {{ margin: 0; padding: 12px; overflow-x: auto; }}
        .codeblock code {{ font-family: Consolas, Monaco, monospace; font-size: 0.85rem; color: #38bdf8; }}
        .quote {{ border-left: 4px solid var(--text-muted); margin: 6px 0; padding-left: 12px; color: var(--text-muted); }}
        .emoji {{ width: 22px; height: 22px; vertical-align: middle; }}
        .mention {{ background: rgba(88, 101, 242, 0.2); color: #c9cdfb; font-weight: 600; padding: 1px 4px; border-radius: 3px; }}
        .role-mention {{ background: rgba(245, 158, 11, 0.2); color: #fcd34d; }}
        .everyone-mention {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; }}
        .chat-link {{ color: #00aff4; text-decoration: none; }}
        .chat-link:hover {{ text-decoration: underline; }}
        .spoiler {{ background: #111214; color: transparent; padding: 1px 6px; border-radius: 3px; cursor: pointer; user-select: none; }}
        .spoiler-revealed {{ background: rgba(255,255,255,0.1); color: var(--text-normal); }}

        /* Bottom Ticket Closed Banner */
        .transcript-closed-card {{
            background: #111214;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 16px 20px;
            margin-top: 30px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            font-size: 0.9rem;
        }}
        .closed-by-row {{
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-white);
        }}
        .closed-lock-icon {{ font-size: 1.1rem; }}
        .closer-avatar {{
            width: 22px;
            height: 22px;
            border-radius: 50%;
            object-fit: cover;
        }}
        .closer-name {{ font-weight: 700; }}
        .closed-reason-row {{ color: var(--text-normal); }}
        .closed-time-row {{ color: var(--text-muted); font-size: 0.8rem; margin-top: 2px; }}
    </style>
</head>
<body>
    <div class="top-nav-bar">
        <div class="top-nav-brand">
            <img src="{server_icon}" class="top-nav-icon" alt="icon">
            <span class="top-nav-title">{server_name}</span>
        </div>
    </div>

    <div class="transcript-main">
        {chat_html}

        <div class="transcript-closed-card">
            <div class="closed-by-row">
                <span class="closed-lock-icon">🔒</span>
                <span><strong>Ticket closed by:</strong></span>
                <img src="{closer_avatar}" class="closer-avatar">
                <span class="closer-name">{closer_name}</span>
            </div>
            <div class="closed-reason-row">
                <strong>Reason:</strong> {html.escape(close_reason)}
            </div>
            <div class="closed-time-row">
                Transcript generated at: {generation_time_str}
            </div>
        </div>
    </div>
</body>
</html>
'''
    return full_html
