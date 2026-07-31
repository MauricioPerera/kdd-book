const COLOR_VARIANTS = {
  blue: 'bg-blue-600 text-white p-4',
  red: 'bg-red-600 text-white p-4',
};

function Card({ color }) {
  return <div className={COLOR_VARIANTS[color]}>Tarjeta</div>;
}
