import React, { useState } from "react";

interface TableInsertDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onInsert: (rows: number, cols: number, withHeader: boolean) => void;
}

export default function TableInsertDialog({
    isOpen,
    onClose,
    onInsert,
}: TableInsertDialogProps) {
    const [rows, setRows] = useState(3);
    const [cols, setCols] = useState(3);
    const [withHeader, setWithHeader] = useState(true);

    if (!isOpen) return null;

    const handleInsert = () => {
        onInsert(rows, cols, withHeader);
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="w-full max-w-md rounded-xl border border-zinc-800 bg-zinc-900 p-6">
                <h2 className="mb-4 text-lg font-semibold text-zinc-100">
                    Insert Table
                </h2>

                <div className="space-y-4">
                    <div>
                        <label className="mb-1 block text-sm text-zinc-300">Rows</label>
                        <input
                            type="number"
                            min="1"
                            max="20"
                            value={rows}
                            onChange={(e) => setRows(parseInt(e.target.value) || 1)}
                            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                        />
                    </div>

                    <div>
                        <label className="mb-1 block text-sm text-zinc-300">Columns</label>
                        <input
                            type="number"
                            min="1"
                            max="10"
                            value={cols}
                            onChange={(e) => setCols(parseInt(e.target.value) || 1)}
                            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                        />
                    </div>

                    <div className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="withHeader"
                            checked={withHeader}
                            onChange={(e) => setWithHeader(e.target.checked)}
                            className="h-4 w-4 rounded border-zinc-800 bg-zinc-950"
                        />
                        <label htmlFor="withHeader" className="text-sm text-zinc-300">
                            Include header row
                        </label>
                    </div>

                    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
                        <div className="text-xs text-zinc-500">Preview</div>
                        <div className="mt-2 overflow-auto">
                            <table className="w-full border-collapse text-xs">
                                <thead>
                                    {withHeader && (
                                        <tr>
                                            {Array.from({ length: cols }).map((_, i) => (
                                                <th
                                                    key={i}
                                                    className="border border-zinc-700 bg-zinc-800 px-2 py-1"
                                                >
                                                    Header {i + 1}
                                                </th>
                                            ))}
                                        </tr>
                                    )}
                                </thead>
                                <tbody>
                                    {Array.from({ length: withHeader ? rows - 1 : rows }).map(
                                        (_, i) => (
                                            <tr key={i}>
                                                {Array.from({ length: cols }).map((_, j) => (
                                                    <td
                                                        key={j}
                                                        className="border border-zinc-700 px-2 py-1"
                                                    >
                                                        Cell
                                                    </td>
                                                ))}
                                            </tr>
                                        ),
                                    )}
                                </tbody>
                            </table>
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
                        Insert Table
                    </button>
                </div>
            </div>
        </div>
    );
}
