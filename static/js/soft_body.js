// 水風船ふうの局所変形。輪郭を制御点リングにして、掴んだ点はカーソルに固定し、
// 他の点は慣性で遅れて流れ、元の風船形(rest)へバネで戻る。引けば尖って伸び、押せば凹む。
var powanSoftBody = {
  count: 24,
  shapeStiffness: 118,
  edgeStiffness: 72,
  dampDrag: 10,
  maxStep: 0.032,
  restSpeed: 6,
  restOffset: 1.6,

  create(width, height) {
    const cx = width / 2;
    const cy = height / 2;
    const rx = Math.max(1, width / 2);
    const ry = Math.max(1, height / 2);
    const points = [];
    for (let i = 0; i < this.count; i++) {
      const angle = (i / this.count) * Math.PI * 2;
      const x = cx + Math.cos(angle) * rx;
      const y = cy + Math.sin(angle) * ry;
      points.push({ x, y, restX: x, restY: y, vx: 0, vy: 0 });
    }
    return { points, count: this.count, cx, cy };
  },

  // 待機中もぷよぷよ揺れるよう、静止形を中心まわりで微小に脈動させた目標点を返す。
  breathedRest(softBody, index, time) {
    const point = softBody.points[index];
    const wobble = 1 + 0.045 * Math.sin(time * 1.8 + index * 0.8) + 0.026 * Math.sin(time * 1.1 + index * 1.7);
    return {
      x: softBody.cx + (point.restX - softBody.cx) * wobble,
      y: softBody.cy + (point.restY - softBody.cy) * wobble,
    };
  },

  applyBreathing(softBody, time = 0) {
    softBody.points.forEach((point, index) => {
      const rest = this.breathedRest(softBody, index, time);
      point.x = rest.x;
      point.y = rest.y;
      point.vx = 0;
      point.vy = 0;
    });
    return softBody;
  },

  grabIndex(softBody, grabX, grabY) {
    let index = 0;
    let best = Infinity;
    softBody.points.forEach((point, i) => {
      const distance = Math.hypot(point.restX - grabX, point.restY - grabY);
      if (distance < best) {
        best = distance;
        index = i;
      }
    });
    return index;
  },

  // moveX/moveY: このフレームで要素が動いたローカル量。掴み点以外を逆向きに取り残して慣性を作る。
  step(softBody, { dt, moveX, moveY, grabIndex, released, time = 0, grabTargetX = null, grabTargetY = null }) {
    const points = softBody.points;
    const n = softBody.count;
    const step = Math.min(Math.max(dt, 0.001), this.maxStep);
    const damp = this.dampDrag;

    for (let i = 0; i < n; i++) {
      if (i === grabIndex && !released) {
        continue;
      }
      const point = points[i];
      point.x -= moveX;
      point.y -= moveY;
    }

    for (let i = 0; i < n; i++) {
      const point = points[i];
      const rest = this.breathedRest(softBody, i, time);
      if (i === grabIndex && !released) {
        point.x = Number.isFinite(grabTargetX) ? grabTargetX : rest.x;
        point.y = Number.isFinite(grabTargetY) ? grabTargetY : rest.y;
        point.vx = 0;
        point.vy = 0;
        continue;
      }
      const prev = points[(i - 1 + n) % n];
      const next = points[(i + 1) % n];
      const midX = (prev.x + next.x) / 2;
      const midY = (prev.y + next.y) / 2;
      const ax = (rest.x - point.x) * this.shapeStiffness + (midX - point.x) * this.edgeStiffness - point.vx * damp;
      const ay = (rest.y - point.y) * this.shapeStiffness + (midY - point.y) * this.edgeStiffness - point.vy * damp;
      point.vx += ax * step;
      point.vy += ay * step;
    }

    let maxSpeed = 0;
    let maxOffset = 0;
    for (let i = 0; i < n; i++) {
      const point = points[i];
      if (!(i === grabIndex && !released)) {
        point.x += point.vx * step;
        point.y += point.vy * step;
      }
      maxSpeed = Math.max(maxSpeed, Math.hypot(point.vx, point.vy));
      const rest = this.breathedRest(softBody, i, time);
      maxOffset = Math.max(maxOffset, Math.hypot(rest.x - point.x, rest.y - point.y));
    }
    return { settled: released && maxSpeed < this.restSpeed && maxOffset < this.restOffset };
  },

  toPathData(softBody) {
    const points = softBody.points;
    const n = softBody.count;
    let data = "";
    for (let i = 0; i < n; i++) {
      const p0 = points[(i - 1 + n) % n];
      const p1 = points[i];
      const p2 = points[(i + 1) % n];
      const p3 = points[(i + 2) % n];
      if (i === 0) {
        data += `M ${p1.x.toFixed(2)} ${p1.y.toFixed(2)} `;
      }
      const c1x = p1.x + (p2.x - p0.x) / 6;
      const c1y = p1.y + (p2.y - p0.y) / 6;
      const c2x = p2.x - (p3.x - p1.x) / 6;
      const c2y = p2.y - (p3.y - p1.y) / 6;
      data += `C ${c1x.toFixed(2)} ${c1y.toFixed(2)}, ${c2x.toFixed(2)} ${c2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)} `;
    }
    data += "Z";
    return data;
  },
};
