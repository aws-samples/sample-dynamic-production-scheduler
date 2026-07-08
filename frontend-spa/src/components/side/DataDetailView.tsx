import { useStore } from "@/store";

export function DataDetailView() {
  const detailData = useStore((s) => s.sidePanel.detailData);
  const closeDetail = useStore((s) => s.closeDetail);

  if (!detailData) return null;

  const entries = Object.entries(detailData.data);

  return (
    <div className="space-y-3 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          {detailData.title}
        </h3>
        <button
          data-testid="detail-view-close-btn"
          className="min-h-11 min-w-11 rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 hover:text-gray-700"
          onClick={closeDetail}
          aria-label="Close detail view"
        >
          Close
        </button>
      </div>
      {Array.isArray(detailData.data.rows) ? (
        <table className="w-full text-xs text-gray-600">
          <tbody>
            {(detailData.data.rows as Record<string, unknown>[]).map((row, i) => (
              <tr key={i} className="border-b border-gray-200">
                {Object.values(row).map((val, j) => (
                  <td key={j} className="py-1 pr-2">{String(val)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <dl className="space-y-1 text-xs">
          {entries.map(([key, val]) => (
            <div key={key} className="flex gap-2">
              <dt className="text-gray-400">{key}:</dt>
              <dd className="text-gray-600">{String(val)}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
