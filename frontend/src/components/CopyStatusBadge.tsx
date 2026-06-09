/**
 * CopyStatusBadge — colored chip for physical copy status.
 * available: green; on_loan: yellow; lost: red; withdrawn: gray
 */
type CopyStatus = "available" | "on_loan" | "lost" | "withdrawn";

interface CopyStatusBadgeProps {
  status: CopyStatus;
}

const STATUS_MAP: Record<CopyStatus, { label: string; colorClass: string }> = {
  available: { label: "Available", colorClass: "bg-green-100 text-green-700" },
  on_loan: { label: "On Loan", colorClass: "bg-yellow-100 text-yellow-700" },
  lost: { label: "Lost", colorClass: "bg-red-100 text-red-700" },
  withdrawn: { label: "Withdrawn", colorClass: "bg-gray-100 text-gray-500" },
};

export default function CopyStatusBadge({ status }: CopyStatusBadgeProps) {
  const entry = STATUS_MAP[status] ?? { label: status, colorClass: "bg-gray-100 text-gray-500" };
  const { label, colorClass } = entry;

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded-full ${colorClass}`}
    >
      {label}
    </span>
  );
}
