import { useState, useEffect, useRef, useMemo } from "react";

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [keyword, setKeyword] = useState("");
  const [radius, setRadius] = useState(3);
  const [myLocation, setMyLocation] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState({});
  const [expandedPlaces, setExpandedPlaces] = useState({});

  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const markersRef = useRef([]);
  const myLocationOverlayRef = useRef(null);

  useEffect(() => {
    if (!window.kakao) {
      setError("카카오맵 SDK를 불러오지 못했어요. index.html의 appkey를 확인하세요.");
      return;
    }
    window.kakao.maps.load(() => {
      const container = mapRef.current;
      const options = {
        center: new window.kakao.maps.LatLng(37.5735, 126.9788),
        level: 6,
      };
      mapInstance.current = new window.kakao.maps.Map(container, options);
    });
  }, []);

  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setError("이 브라우저는 위치 기능을 지원하지 않아요.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        setMyLocation({ lat, lng });
        setError("");

        if (mapInstance.current) {
          const moveLatLng = new window.kakao.maps.LatLng(lat, lng);
          mapInstance.current.setCenter(moveLatLng);

          if (myLocationOverlayRef.current) {
            myLocationOverlayRef.current.setMap(null);
          }

          const content = `
            <div style="
              width: 16px; height: 16px;
              background: #4285F4;
              border: 3px solid white;
              border-radius: 50%;
              box-shadow: 0 0 4px rgba(0,0,0,0.4);
            "></div>
          `;
          const overlay = new window.kakao.maps.CustomOverlay({
            position: moveLatLng,
            content: content,
            map: mapInstance.current,
            yAnchor: 0.5,
          });
          myLocationOverlayRef.current = overlay;
        }
      },
      (err) => {
        setError("위치 권한을 허용해주세요. (" + err.message + ")");
      }
    );
  };

  const clearMarkers = () => {
    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];
  };

  const handleSearch = async () => {
    if (!keyword.trim()) return;
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({ keyword });
      if (myLocation) {
        params.append("lat", myLocation.lat);
        params.append("lng", myLocation.lng);
        params.append("radius", radius);
      }

      const res = await fetch(`${API_BASE}/search?${params.toString()}`);
      if (!res.ok) throw new Error("서버 응답 오류");
      const data = await res.json();
      setResults(data.results);

      // 검색결과에 등장하는 상태값들을 기준으로 필터 체크박스 초기화 (전부 체크된 상태로 시작)
      const uniqueStatuses = [...new Set(data.results.map((r) => r.서비스상태))];
      const initialFilter = {};
      uniqueStatuses.forEach((s) => (initialFilter[s] = true));
      setStatusFilter(initialFilter);
      setExpandedPlaces({});

      clearMarkers();
      if (mapInstance.current && data.results.length > 0) {
        const bounds = new window.kakao.maps.LatLngBounds();

        const redMarkerSvg = `
          <svg xmlns="http://www.w3.org/2000/svg" width="32" height="42" viewBox="0 0 32 42">
            <path d="M16 0C7.163 0 0 7.163 0 16c0 12 16 26 16 26s16-14 16-26C32 7.163 24.837 0 16 0z" fill="#EA4335"/>
            <circle cx="16" cy="16" r="6" fill="white"/>
          </svg>
        `;
        const markerImage = new window.kakao.maps.MarkerImage(
          "data:image/svg+xml;charset=utf-8," + encodeURIComponent(redMarkerSvg),
          new window.kakao.maps.Size(32, 42),
          { offset: new window.kakao.maps.Point(16, 42) }
        );

        data.results.forEach((item) => {
          const position = new window.kakao.maps.LatLng(item.lat, item.lng);
          const marker = new window.kakao.maps.Marker({
            position,
            map: mapInstance.current,
            image: markerImage,
          });

          const infoContent = `
            <div style="padding:8px;font-size:13px;max-width:220px;">
              <strong>${item.서비스명}</strong><br/>
              ${item.장소명}<br/>
              상태: ${item.서비스상태}<br/>
              ${item.거리_km !== undefined ? `거리: ${item.거리_km}km<br/>` : ""}
              <a href="${item.예약URL}" target="_blank">예약 페이지 이동</a>
            </div>
          `;
          const infoWindow = new window.kakao.maps.InfoWindow({ content: infoContent });

          window.kakao.maps.event.addListener(marker, "click", () => {
            infoWindow.open(mapInstance.current, marker);
          });

          markersRef.current.push(marker);
          bounds.extend(position);
        });

        if (myLocation) {
          bounds.extend(new window.kakao.maps.LatLng(myLocation.lat, myLocation.lng));
        }

        mapInstance.current.setBounds(bounds);
      }
    } catch (e) {
      setError("검색 중 오류가 발생했어요: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleStatusFilter = (status) => {
    setStatusFilter((prev) => ({ ...prev, [status]: !prev[status] }));
  };

  const togglePlace = (placeName) => {
    setExpandedPlaces((prev) => ({ ...prev, [placeName]: !prev[placeName] }));
  };

  // 상태 필터 적용
  const filteredResults = useMemo(() => {
    return results.filter((item) => statusFilter[item.서비스상태]);
  }, [results, statusFilter]);

  // 장소명(placenm) 기준으로 그룹핑
  const groupedByPlace = useMemo(() => {
    const groups = {};
    filteredResults.forEach((item) => {
      const key = item.장소명 || "기타";
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
    });
    return groups;
  }, [filteredResults]);

  const allStatuses = Object.keys(statusFilter);

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 20, fontFamily: "sans-serif" }}>
      <h2>BENE 근처 프로그램 찾기 (테스트)</h2>

      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        <input
          type="text"
          placeholder="배우고 싶은 것을 검색하세요 (예: 테니스)"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          style={{ flex: 1, minWidth: 200, padding: 8 }}
        />
        <button onClick={handleGetLocation} style={{ padding: 8 }}>
          내 위치 설정 {myLocation && "✓"}
        </button>
        <select value={radius} onChange={(e) => setRadius(Number(e.target.value))} style={{ padding: 8 }}>
          <option value={1}>1km</option>
          <option value={3}>3km</option>
          <option value={5}>5km</option>
          <option value={10}>10km</option>
        </select>
        <button onClick={handleSearch} disabled={loading} style={{ padding: 8 }}>
          {loading ? "검색 중..." : "검색"}
        </button>
      </div>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <div style={{ display: "flex", gap: 16, marginBottom: 8, fontSize: 13, color: "#555" }}>
        <span>
          <span style={{ display: "inline-block", width: 10, height: 10, background: "#4285F4", borderRadius: "50%", marginRight: 4 }}></span>
          내 위치
        </span>
        <span>
          <span style={{ display: "inline-block", width: 10, height: 10, background: "red", borderRadius: "50%", marginRight: 4 }}></span>
          검색결과
        </span>
      </div>

      <div ref={mapRef} style={{ width: "100%", height: 400, marginBottom: 16, border: "1px solid #ddd" }} />

      {allStatuses.length > 0 && (
        <div style={{ marginBottom: 12, display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: 14, fontWeight: "bold" }}>상태:</span>
          {allStatuses.map((status) => (
            <label key={status} style={{ fontSize: 14, display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={statusFilter[status]}
                onChange={() => toggleStatusFilter(status)}
              />
              {status}
            </label>
          ))}
        </div>
      )}

      <p>검색 결과: {filteredResults.length}건 ({Object.keys(groupedByPlace).length}개 장소)</p>

      <div>
        {Object.entries(groupedByPlace).map(([placeName, items]) => {
          const isExpanded = expandedPlaces[placeName];
          return (
            <div key={placeName} style={{ marginBottom: 8, border: "1px solid #eee", borderRadius: 6, overflow: "hidden" }}>
              <div
                onClick={() => togglePlace(placeName)}
                style={{
                  padding: "10px 12px",
                  background: "#f7f7f7",
                  cursor: "pointer",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  fontWeight: "bold",
                }}
              >
                <span>{isExpanded ? "▼" : "▶"} {placeName} ({items.length}건)</span>
              </div>

              {isExpanded && (
                <div style={{ padding: "4px 12px" }}>
                  {items.map((item, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: "8px 0",
                        borderTop: idx > 0 ? "1px solid #f0f0f0" : "none",
                      }}
                    >
                      <div style={{ fontSize: 14 }}>
                        {item.서비스명} · {item.서비스상태}
                        {item.거리_km !== undefined && ` · ${item.거리_km}km`}
                      </div>
                      {item.예약URL && (
                        
                          <a href={item.예약URL}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ fontSize: 13, color: "#4285F4" }}
                        >
                          신청하러 가기 →
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default App;