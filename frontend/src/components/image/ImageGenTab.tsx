import React, { useState } from 'react';
import { imageService } from '../../services/imageService';
import { useToast } from '../../context/ToastContext';
import {
  Palette,
  Sparkles,
  Wand2,
  Image as ImageIcon,
  Maximize2,
  Download,
  X,
  Loader2
} from 'lucide-react';

const STYLES = [
  { id: 'none', label: 'Mặc định', icon: '🎨' },
  { id: 'photorealistic', label: 'Chụp Đời Thật (DSLR)', icon: '📸', desc: 'Ảnh chụp chân thực như máy ảnh ngoài đời thực' },
  { id: 'anime', label: 'Anime Manga', icon: '⛩️' },
  { id: 'cyberpunk', label: 'Cyberpunk', icon: '🌆' },
  { id: 'oil_painting', label: 'Sơn dầu', icon: '🖌️' },
  { id: '3d_render', label: '3D Pixar', icon: '🔮' },
];

const RATIOS = [
  { id: '1:1', title: '1:1', subtitle: 'Vuông' },
  { id: '16:9', title: '16:9', subtitle: 'Ngang' },
  { id: '9:16', title: '9:16', subtitle: 'Dọc Story' },
  { id: '4:3', title: '4:3', subtitle: 'Chuẩn' },
  { id: '3:4', title: '3:4', subtitle: 'Chân dung' },
];

export const ImageGenTab: React.FC = () => {
  const { showToast } = useToast();

  const [prompt, setPrompt] = useState('');
  const [selectedStyle, setSelectedStyle] = useState('none');
  const [selectedRatio, setSelectedRatio] = useState('1:1');
  const [selectedModel, setSelectedModel] = useState('flux');
  const [loading, setLoading] = useState(false);
  const [enhancing, setEnhancing] = useState(false);

  // Result state
  const [activeImage, setActiveImage] = useState<{
    url: string;
    prompt: string;
    model: string;
    size: string;
  } | null>(null);

  // Lightbox
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);

  // Recent gallery
  const [gallery, setGallery] = useState<Array<{ id: string; url: string; prompt: string; model: string }>>(() => {
    const saved = localStorage.getItem('antigravity_image_gallery');
    return saved ? JSON.parse(saved) : [];
  });

  const handleEnhancePrompt = async () => {
    if (!prompt.trim()) {
      showToast('Vui lòng nhập mô tả ảnh trước khi tối ưu!', 'info');
      return;
    }
    setEnhancing(true);
    try {
      const res = await imageService.enhancePrompt(prompt.trim(), selectedStyle === 'none' ? undefined : selectedStyle);
      if (res.enhanced_prompt) {
        setPrompt(res.enhanced_prompt);
        showToast('Đã dùng Gemini tối ưu prompt sáng tạo!', 'success');
      }
    } catch (err: any) {
      showToast(err.message || 'Lỗi tối ưu prompt', 'error');
    } finally {
      setEnhancing(false);
    }
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      showToast('Vui lòng nhập mô tả bức ảnh muốn tạo!', 'error');
      return;
    }

    setLoading(true);
    try {
      const res = await imageService.generateImage({
        prompt: prompt.trim(),
        style: selectedStyle === 'none' ? undefined : selectedStyle,
        aspect_ratio: selectedRatio,
        model: selectedModel,
      });

      const imageUrl = res.image_url || res.data || '';
      if (!imageUrl) throw new Error('Không nhận được ảnh trả về từ mô hình!');

      const newArtwork = {
        url: imageUrl,
        prompt: prompt.trim(),
        model: selectedModel === 'flux' ? 'Flux.1' : selectedModel === 'turbo' ? 'SDXL Turbo' : 'Pollinations',
        size: selectedRatio === '1:1' ? '1024x1024' : selectedRatio === '16:9' ? '1280x720' : selectedRatio === '9:16' ? '720x1280' : '1024x768',
      };

      setActiveImage(newArtwork);

      const updatedGallery = [{ id: 'img_' + Date.now(), ...newArtwork }, ...gallery];
      setGallery(updatedGallery);
      localStorage.setItem('antigravity_image_gallery', JSON.stringify(updatedGallery));

      showToast('Tạo ảnh nghệ thuật thành công!', 'success');
    } catch (err: any) {
      showToast(err.message || 'Lỗi khi tạo ảnh', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleClearGallery = () => {
    if (!window.confirm('Bạn có chắc muốn xóa lịch sử ảnh vừa tạo?')) return;
    setGallery([]);
    localStorage.removeItem('antigravity_image_gallery');
    showToast('Đã xóa lịch sử thư viện ảnh!', 'info');
  };

  return (
    <div className="flex flex-col gap-6 min-h-0 overflow-y-auto pr-1 pb-8">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/60 p-5 border border-slate-800 rounded-2xl shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-pink-500 to-rose-500 flex items-center justify-center text-white shadow-lg shadow-pink-500/20">
            <Palette className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-base text-white">Xưởng Sáng Tạo Hình Ảnh AI (Image Studio)</h3>
            <p className="text-xs text-slate-400">
              Tạo hình ảnh nghệ thuật siêu nét với Flux.1 & SDXL Turbo, tự động nâng cấp prompt bằng Gemini.
            </p>
          </div>
        </div>
      </div>

      {/* Studio Grid: Left Controls (5 cols) / Right Canvas (7 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT: Controls (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-md">
            {/* Prompt Input */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Mô tả bức ảnh (*):
                </label>
                <button
                  type="button"
                  onClick={handleEnhancePrompt}
                  disabled={enhancing}
                  className="text-xs text-purple-400 hover:text-purple-300 flex items-center space-x-1 transition font-medium disabled:opacity-50"
                >
                  <Sparkles className={`w-3.5 h-3.5 ${enhancing ? 'animate-spin' : ''}`} />
                  <span>{enhancing ? 'Đang tối ưu...' : 'Tối ưu bằng Gemini'}</span>
                </button>
              </div>
              <textarea
                rows={4}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Nhập ý tưởng bằng tiếng Việt hoặc tiếng Anh (ví dụ: 'Một chú mèo phi hành gia câu cá giữa các vì sao cyberpunk neon')..."
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-pink-500 resize-none"
              />
            </div>

            {/* Style Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Phong cách nghệ thuật:
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {STYLES.map((st) => (
                  <button
                    key={st.id}
                    type="button"
                    onClick={() => setSelectedStyle(st.id)}
                    title={st.desc}
                    className={`px-2.5 py-1.5 rounded-xl border text-xs font-medium transition text-left flex items-center space-x-1.5 ${
                      selectedStyle === st.id
                        ? 'border-pink-500 bg-pink-500/10 text-pink-300'
                        : 'border-slate-800 bg-slate-950 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <span>{st.icon}</span>
                    <span>{st.label}</span>
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-slate-500 mt-1.5">
                💡 Muốn ảnh giống ngoài đời: Chọn <b>📸 Chụp Đời Thật</b> rồi bấm <b>✨ Tối ưu bằng Gemini</b>.
              </p>
            </div>

            {/* Aspect Ratio Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Tỉ lệ khung hình:
              </label>
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-1.5">
                {RATIOS.map((rt) => (
                  <button
                    key={rt.id}
                    type="button"
                    onClick={() => setSelectedRatio(rt.id)}
                    className={`p-2 rounded-xl border text-xs font-medium transition text-center ${
                      selectedRatio === rt.id
                        ? 'border-pink-500 bg-pink-500/10 text-pink-300'
                        : 'border-slate-800 bg-slate-950 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="font-bold">{rt.title}</div>
                    <div className="text-[10px] opacity-75">{rt.subtitle}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Model Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Mô hình AI tạo ảnh:
              </label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-pink-500 cursor-pointer"
              >
                <option value="flux">Flux.1 (Sắc nét đỉnh cao, giàu chi tiết)</option>
                <option value="turbo">SDXL Turbo (Tạo siêu tốc 1-3s)</option>
                <option value="default">Pollinations General (Tự động cân bằng)</option>
              </select>
            </div>

            {/* Generate Button */}
            <button
              type="button"
              onClick={handleGenerate}
              disabled={loading || !prompt.trim()}
              className="w-full py-3 bg-gradient-to-r from-pink-600 via-rose-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 text-white rounded-xl font-medium transition shadow-lg shadow-pink-600/30 flex items-center justify-center space-x-2 disabled:opacity-50 active:scale-95"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
              <span>{loading ? 'Đang vẽ tác phẩm...' : 'Tạo Ảnh Ngay'}</span>
            </button>
          </div>
        </div>

        {/* RIGHT: Display Canvas & Gallery (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          {/* Active Preview Frame */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-4 min-h-[440px] flex flex-col items-center justify-center relative overflow-hidden shadow-md">
            {loading ? (
              /* Loading State */
              <div className="flex flex-col items-center justify-center space-y-3 py-16">
                <div className="w-14 h-14 rounded-full border-4 border-pink-500/30 border-t-pink-500 animate-spin"></div>
                <p className="text-sm font-medium text-slate-200">Đang kiến tạo tác phẩm với AI...</p>
                <p className="text-xs text-slate-400">Ảnh đang được tạo trực tiếp từ AI engine...</p>
              </div>
            ) : activeImage ? (
              /* Rendered Image Frame */
              <div className="w-full flex flex-col items-center space-y-3">
                <div className="relative group rounded-xl overflow-hidden border border-slate-700 max-h-[460px] flex items-center justify-center bg-black/40">
                  <img
                    src={activeImage.url}
                    alt="AI Artwork"
                    onClick={() => setLightboxUrl(activeImage.url)}
                    className="max-h-[460px] w-auto object-contain rounded-xl cursor-pointer transition hover:scale-[1.01]"
                  />
                </div>

                {/* Action Bar for active image */}
                <div className="w-full flex items-center justify-between pt-2 border-t border-slate-800 text-xs">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 rounded bg-pink-500/10 text-pink-400 border border-pink-500/20 text-[10px] font-bold">
                      {activeImage.model}
                    </span>
                    <span className="text-slate-400 text-[11px]">{activeImage.size}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setLightboxUrl(activeImage.url)}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition flex items-center space-x-1"
                    >
                      <Maximize2 className="w-3.5 h-3.5" />
                      <span>Phóng to</span>
                    </button>
                    <a
                      href={activeImage.url}
                      target="_blank"
                      rel="noreferrer"
                      download="ai-artwork.jpg"
                      className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition flex items-center space-x-1 font-medium"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Tải về</span>
                    </a>
                  </div>
                </div>

                {/* Enhanced prompt box */}
                <div className="w-full bg-slate-950/80 border border-slate-800 rounded-xl p-3 text-xs text-slate-300">
                  <span className="text-purple-400 font-semibold">Prompt chi tiết:</span>
                  <p className="italic text-slate-400 mt-0.5 text-[11px] leading-relaxed">
                    {activeImage.prompt}
                  </p>
                </div>
              </div>
            ) : (
              /* Default Empty State */
              <div className="text-center py-12 px-4 max-w-sm">
                <div className="w-16 h-16 rounded-2xl bg-pink-500/10 border border-pink-500/20 text-pink-400 flex items-center justify-center mx-auto mb-4 shadow">
                  <ImageIcon className="w-8 h-8" />
                </div>
                <h4 className="font-bold text-white text-base mb-1">Chưa có tác phẩm nào</h4>
                <p className="text-xs text-slate-400 mb-4 leading-relaxed">
                  Nhập mô tả ở khung bên trái và nhấn nút "Tạo Ảnh Ngay" để AI bắt đầu vẽ tác phẩm của bạn.
                </p>
                <button
                  onClick={() => setPrompt('Một chú cá rồng vàng bơi trong dải ngân hà lấp lánh sao, phong cách cyberpunk neon 8k')}
                  className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition border border-slate-700/60"
                >
                  💡 Thử prompt mẫu: "Cá rồng ngân hà..."
                </button>
              </div>
            )}
          </div>

          {/* Recent Gallery */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Thư viện tác phẩm vừa tạo:
              </span>
              {gallery.length > 0 && (
                <button
                  onClick={handleClearGallery}
                  className="text-[11px] text-slate-500 hover:text-red-400 transition"
                >
                  Xóa lịch sử
                </button>
              )}
            </div>

            {gallery.length === 0 ? (
              <div className="min-h-[70px] flex items-center justify-center">
                <p className="text-xs text-slate-500 py-4 text-center">Các ảnh vừa vẽ sẽ xuất hiện tại đây.</p>
              </div>
            ) : (
              <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
                {gallery.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => {
                      setActiveImage({
                        url: item.url,
                        prompt: item.prompt,
                        model: item.model || 'Flux.1',
                        size: '1024x1024',
                      });
                    }}
                    className="group relative aspect-square rounded-xl overflow-hidden border border-slate-800 hover:border-pink-500/50 cursor-pointer transition"
                  >
                    <img src={item.url} alt="" className="w-full h-full object-cover transition group-hover:scale-105" />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                      <Maximize2 className="w-4 h-4 text-white" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Lightbox Modal */}
      {lightboxUrl && (
        <div
          onClick={() => setLightboxUrl(null)}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-md animate-in fade-in duration-200"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="relative max-w-5xl max-h-[90vh] bg-slate-900 border border-slate-800 rounded-2xl p-2 shadow-2xl flex flex-col items-center"
          >
            <button
              onClick={() => setLightboxUrl(null)}
              className="absolute top-4 right-4 p-2 rounded-xl bg-slate-950/80 hover:bg-slate-800 text-slate-400 hover:text-white transition border border-slate-800 z-10"
            >
              <X className="w-5 h-5" />
            </button>
            <img
              src={lightboxUrl}
              alt="Full Preview"
              className="max-h-[82vh] w-auto object-contain rounded-xl"
            />
            <div className="w-full flex items-center justify-between pt-3 px-3">
              <a
                href={lightboxUrl}
                target="_blank"
                rel="noreferrer"
                download="artwork-full.jpg"
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition shadow-lg shadow-blue-600/20"
              >
                <Download className="w-4 h-4" />
                <span>Tải ảnh gốc</span>
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
