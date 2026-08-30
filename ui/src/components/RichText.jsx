/* A deliberately small Markdown subset for model replies.

   Models emit **bold** and numbered lists whether or not you ask them to, and
   showing the raw asterisks makes the coach look broken. Rather than fight that
   in the prompt, render the handful of things they actually use.

   Everything is built as React elements, never dangerouslySetInnerHTML: the text
   comes from a language model reading user-supplied context, so it is untrusted
   by definition and must never be able to inject markup. */

const INLINE = /(\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|`[^`\n]+`)/g;
const ORDERED = /^\s*(\d{1,2})[.)]\s+(.*)$/;
const BULLET = /^\s*[-*•]\s+(.*)$/;

function inline(text, keyBase) {
  return text.split(INLINE).filter(Boolean).map((part, i) => {
    const key = `${keyBase}-${i}`;
    if ((part.startsWith('**') && part.endsWith('**')) || (part.startsWith('__') && part.endsWith('__'))) {
      return <strong key={key}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return <em key={key}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={key}>{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

export default function RichText({ text }) {
  const lines = String(text || '').split('\n');
  const blocks = [];
  let paragraph = [];
  let list = null;          // { type: 'ol' | 'ul', items: [] }

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const key = `p-${blocks.length}`;
    blocks.push(
      <p key={key}>
        {paragraph.map((line, i) => (
          <span key={`${key}-${i}`}>
            {i > 0 && <br />}
            {inline(line, `${key}-${i}`)}
          </span>
        ))}
      </p>,
    );
    paragraph = [];
  };

  const flushList = () => {
    if (!list) return;
    const key = `l-${blocks.length}`;
    const Tag = list.type;
    blocks.push(
      <Tag key={key} className="rich-list">
        {list.items.map((item, i) => <li key={`${key}-${i}`}>{inline(item, `${key}-${i}`)}</li>)}
      </Tag>,
    );
    list = null;
  };

  for (const line of lines) {
    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }
    const ordered = line.match(ORDERED);
    const bullet = line.match(BULLET);
    if (ordered || bullet) {
      flushParagraph();
      const type = ordered ? 'ol' : 'ul';
      if (!list || list.type !== type) {
        flushList();
        list = { type, items: [] };
      }
      list.items.push((ordered ? ordered[2] : bullet[1]).trim());
      continue;
    }
    flushList();
    paragraph.push(line);
  }
  flushParagraph();
  flushList();

  return <>{blocks}</>;
}
