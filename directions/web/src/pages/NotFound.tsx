import { Link } from "react-router";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-[1100px] px-4 py-16 sm:px-6">
      <h1 className="font-serif text-[2.4rem] font-medium">Not in the notebook</h1>
      <p className="mt-2 text-ink-soft">
        There is no page at this address. <Link to="/" className="link">Return to the start</Link>.
      </p>
    </div>
  );
}
