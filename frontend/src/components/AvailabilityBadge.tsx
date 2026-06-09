/**
 * AvailabilityBadge — green chip when copies are available, gray when none.
 * count > 0: green-100/green-700; count === 0: gray-100/gray-500
 */
interface AvailabilityBadgeProps {
  count: number;
}

export default function AvailabilityBadge({ count }: AvailabilityBadgeProps) {
  const colorClass =
    count > 0
      ? "bg-green-100 text-green-700"
      : "bg-gray-100 text-gray-500";

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded-full ${colorClass}`}
    >
      {count} available
    </span>
  );
}
