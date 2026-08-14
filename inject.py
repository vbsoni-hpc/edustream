import base64
import pathlib

with open('drop_b64.txt', 'r') as f:
    b64 = f.read().strip()

path = pathlib.Path('components/notifications.py')
content = path.read_text('utf-8')

b64_str = f"B64_DROP_SOUND = '{b64}'"

lines = content.split('\n')
lines.insert(5, b64_str)

new_content = []
for line in lines:
    new_content.append(line)
    if 'st.toast(' in line:
        indent = line[:line.find('st.toast')]
        audio_line = indent + f"st.markdown(f'<audio autoplay=\"true\" src=\"data:audio/wav;base64,{{B64_DROP_SOUND}}\" style=\"display:none;\"></audio>', unsafe_allow_html=True)"
        new_content.append(audio_line)

path.write_text('\n'.join(new_content), 'utf-8')
print('Injected!')
