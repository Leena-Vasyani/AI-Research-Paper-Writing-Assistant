import React, { useState } from "react";
import "katex/dist/katex.min.css";
import { BlockMath, InlineMath } from "react-katex";

interface EquationEditorProps {
    isOpen: boolean;
    onClose: () => void;
    onInsert: (latex: string, isBlock: boolean) => void;
}

export default function EquationEditor({
    isOpen,
    onClose,
    onInsert,
}: EquationEditorProps) {
    const [latex, setLatex] = useState("E = mc^2");
    const [isBlock, setIsBlock] = useState(false);
    const [error, setError] = useState<string | null>(null);

    if (!isOpen) return null;

    const handleInsert = () => {
        if (!latex.trim()) {
            setError("Please enter a LaTeX expression");
            return;
        }
        onInsert(latex, isBlock);
        onClose();
        setLatex("E = mc^2");
        setError(null);
    };

    const commonSymbols = [
        { label: "α", latex: "\\alpha" },
        { label: "β", latex: "\\beta" },
        { label: "γ", latex: "\\gamma" },
        { label: "δ", latex: "\\delta" },
        { label: "∑", latex: "\\sum" },
        { label: "∫", latex: "\\int" },
        { label: "√", latex: "\\sqrt{}" },
        { label: "∞", latex: "\\infty" },
        { label: "≈", latex: "\\approx" },
        { label: "≠", latex: "\\neq" },
        { label: "≤", latex: "\\leq" },
        { label: "≥", latex: "\\geq" },
        { label: "±", latex: "\\pm" },
        { label: "×", latex: "\\times" },
        { label: "÷", latex: "\\div" },
        { label: "∂", latex: "\\partial" },
    ];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="w-full max-w-2xl rounded-xl border border-zinc-800 bg-zinc-900 p-6">
                <h2 className="mb-4 text-lg font-semibold text-zinc-100">
                    Insert Equation
                </h2>

                <div className="space-y-4">
                    <div>
                        <label className="mb-1 block text-sm text-zinc-300">
                            LaTeX Expression
                        </label>
                        <textarea
                            value={latex}
                            onChange={(e) => {
                                setLatex(e.target.value);
                                setError(null);
                            }}
                            placeholder="Enter LaTeX expression..."
                            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                            rows={3}
                        />
                        {error && <div className="mt-1 text-xs text-rose-400">{error}</div>}
                    </div>

                    <div className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="isBlock"
                            checked={isBlock}
                            onChange={(e) => setIsBlock(e.target.checked)}
                            className="h-4 w-4 rounded border-zinc-800 bg-zinc-950"
                        />
                        <label htmlFor="isBlock" className="text-sm text-zinc-300">
                            Display as block equation (centered)
                        </label>
                    </div>

                    <div>
                        <div className="mb-2 text-xs text-zinc-500">Common Symbols</div>
                        <div className="flex flex-wrap gap-2">
                            {commonSymbols.map((symbol) => (
                                <button
                                    key={symbol.latex}
                                    onClick={() => setLatex((prev) => prev + " " + symbol.latex)}
                                    className="rounded border border-zinc-800 bg-zinc-950 px-2 py-1 text-sm text-zinc-300 hover:bg-zinc-800"
                                    title={symbol.latex}
                                >
                                    {symbol.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
                        <div className="mb-2 text-xs text-zinc-500">Preview</div>
                        <div className="flex min-h-[60px] items-center justify-center text-zinc-100">
                            {latex.trim() ? (
                                <div>
                                    {isBlock ? (
                                        <BlockMath math={latex} errorColor="#f87171" />
                                    ) : (
                                        <InlineMath math={latex} errorColor="#f87171" />
                                    )}
                                </div>
                            ) : (
                                <div className="text-sm text-zinc-500">
                                    Enter LaTeX to see preview
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="mt-6 flex justify-end gap-2">
                    <button
                        onClick={onClose}
                        className="rounded-lg border border-zinc-800 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleInsert}
                        className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400"
                    >
                        Insert Equation
                    </button>
                </div>
            </div>
        </div>
    );
}
