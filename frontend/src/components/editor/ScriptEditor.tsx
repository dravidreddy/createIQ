import React, { useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import { Bold, Italic, Strikethrough, List, ListOrdered, Undo, Redo } from 'lucide-react';
import { clsx } from 'clsx';

interface ScriptEditorProps {
  content: string;
  onChange?: (html: string) => void;
  readOnly?: boolean;
}

export function ScriptEditor({ content, onChange, readOnly = false }: ScriptEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
      }),
      Placeholder.configure({
        placeholder: 'Start writing your script here...',
      }),
    ],
    content,
    editable: !readOnly,
    onUpdate: ({ editor }) => {
      onChange?.(editor.getHTML());
    },
    editorProps: {
      attributes: {
        className: 'prose prose-sm dark:prose-invert max-w-none focus:outline-none min-h-[300px]',
      },
    },
  });

  // Update content if it changes externally
  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content, { emitUpdate: false });
    }
  }, [content, editor]);

  if (!editor) return null;

  return (
    <div className={clsx("rounded-xl border flex flex-col overflow-hidden bg-slate-900 shadow-xl", readOnly ? "border-transparent" : "border-slate-800")}>
      {/* Toolbar */}
      {!readOnly && (
        <div className="flex flex-wrap items-center gap-1 p-2 border-b border-slate-800 bg-slate-950/50 relative z-10 sticky top-0">
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBold().run()}
            active={editor.isActive('bold')}
            icon={<Bold className="w-4 h-4" />}
          />
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleItalic().run()}
            active={editor.isActive('italic')}
            icon={<Italic className="w-4 h-4" />}
          />
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleStrike().run()}
            active={editor.isActive('strike')}
            icon={<Strikethrough className="w-4 h-4" />}
          />
          <div className="w-px h-5 bg-slate-800 mx-1" />
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            active={editor.isActive('heading', { level: 2 })}
            label="H2"
          />
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            active={editor.isActive('heading', { level: 3 })}
            label="H3"
          />
          <div className="w-px h-5 bg-slate-800 mx-1" />
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            active={editor.isActive('bulletList')}
            icon={<List className="w-4 h-4" />}
          />
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            active={editor.isActive('orderedList')}
            icon={<ListOrdered className="w-4 h-4" />}
          />
          <div className="flex-1" />
          <ToolbarButton
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
            icon={<Undo className="w-4 h-4" />}
          />
          <ToolbarButton
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
            icon={<Redo className="w-4 h-4" />}
          />
        </div>
      )}

      {/* Editor Canvas */}
      <div className="p-6 overflow-y-auto">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}

function ToolbarButton({ 
  onClick, 
  active, 
  disabled, 
  icon, 
  label 
}: { 
  onClick: () => void; 
  active?: boolean; 
  disabled?: boolean; 
  icon?: React.ReactNode; 
  label?: string 
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "p-2 rounded-md transition-colors flex items-center justify-center min-w-[32px] h-8",
        active ? "bg-primary-500/20 text-primary-400" : "text-slate-400 hover:text-slate-100 hover:bg-slate-800",
        disabled ? "opacity-50 cursor-not-allowed" : ""
      )}
    >
      {icon}
      {label && <span className="text-sm font-semibold">{label}</span>}
    </button>
  );
}
