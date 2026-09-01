# 005 — Integrate Demo Usage Tracker

## 問題描述
按 Demo Hub 要求，需在已註冊 demo (`ec8ac15b-1b3b-49a3-a3b7-0fa4f7c93488`) 中整合 `demo-usage-tracker-client`，以便：
- 自動追蹤 session（含瀏覽器語言、地區）
- 顯示 Terms of Use modal 並阻擋未接受 ToS 的用戶
- 提示 demo owner 登記 opportunity

## 根本原因（背景）
此前項目沒有任何 usage tracking。要上 Demo Hub 生產，必須先按 [tracker 文檔](https://gitlab.aws.dev/guymor/demo-usage-tracker-client) 完成整合。

## 涉及的文件 / 代碼位置
- `frontend/public/usage-tracker-auto.bundle.min.js`（新增，104 KB，含 marked + DOMPurify）
- `frontend/public/usage-tracker-config.js`（新增，配置 production endpoint 和 demo ID）
- `frontend/public/terms.md`（新增，AWS 標準 ToS）
- `frontend/components/UsageTrackerInit.tsx`（新增，client component，掛載後初始化 `UsageTrackerAuto`）
- `frontend/app/layout.tsx`（修改，注入 two `<Script strategy="beforeInteractive">` 和 `<UsageTrackerInit />`）

## 修改前有什麼問題
無 tracking，無法上線 Demo Hub。

## 具體做了哪些修改
1. 從 GitLab 克隆 `git@ssh.gitlab.aws.dev:guymor/demo-usage-tracker-client.git`。
2. 複製 `usage-tracker-auto.bundle.min.js`、`usage-tracker-config.js`、`terms.md` 到 `frontend/public/`（Next.js 靜態資源根目錄，會被 standalone 構建直接複製到容器 `/app/public/`）。
3. 改寫 `usage-tracker-config.js`：
   ```js
   apiUrl: "https://tracker-api.demohub.portal.aws.dev/track",
   demoId: "ec8ac15b-1b3b-49a3-a3b7-0fa4f7c93488",
   frontendVersion: "1.0.0",
   showToast: true,
   showTerms: true,
   debug: false,
   ```
4. 在 `app/layout.tsx`（server component）裡用 `next/script` 注入 config 和 bundle，`strategy="beforeInteractive"`，保證在 React hydrate 前載入。
5. 新增 `components/UsageTrackerInit.tsx`（client component）：`useEffect` 裡輪詢 `window.UsageTrackerAuto`，可用時呼叫 `new UsageTrackerAuto()`。
6. 部署：`AWS_PROFILE=default bash frontend/frontend-deploy.sh`（build → ECR push → ECS rolling update），完成後 `aws cloudfront create-invalidation` 清緩存。

## 為什麼這樣修改
- **為什麼放 `app/layout.tsx`**：所有頁面都要被 tracker 攔截顯示 ToS modal，layout 是唯一根節點。
- **為什麼用 `next/script beforeInteractive`**：保證 `window.UsageTrackerConfig` 和 `UsageTrackerAuto` 在客戶端任何 React 邏輯運行前就可用，避免 race。
- **為什麼新增 client component 而不直接 inline `<script>`**：layout 是 server component，不能直接寫 `useEffect`；分離出去後職責清晰，並可加 retry / 容錯。
- **為什麼不等用戶登入**：此 demo 對外公開（CloudFront 路由到 ALB→ECS Next.js server），沒有用戶登入流程。Tracker 在頁面載入時就應該初始化，由 `showTerms: true` 自己彈出 modal 攔截訪問。Tracker README 明確說明：若無 Cognito token 則匿名追蹤 session。

## 如何驗證修復有效
1. 本地：`npm run build && PORT=3030 npm start`，curl 三個 asset 都 200，HTML 含兩個 script tag。
2. 生產：
   ```
   curl https://d10lub5i8fbja9.cloudfront.net/usage-tracker-config.js     → 200，內容正確
   curl https://d10lub5i8fbja9.cloudfront.net/usage-tracker-auto.bundle.min.js → 200, 100686 bytes
   curl https://d10lub5i8fbja9.cloudfront.net/terms.md                    → 200, 1355 bytes
   curl https://d10lub5i8fbja9.cloudfront.net/                            → 200, HTML 含兩個 script
   ```
3. 瀏覽器打開 `https://d10lub5i8fbja9.cloudfront.net/`：應彈出 Terms of Use modal，要求滾動到底並勾選同意才能進入 demo；接受後 Network 面板可看到 `POST https://tracker-api.demohub.portal.aws.dev/track` 帶 200 響應。

## 後續可改進點
- 如果以後加入用戶 Cognito 登入，把 `UsageTrackerInit` 從 layout 移到登入後的 routes，並改為在登入成功 callback 中構造，這樣 tracker 能直接從 Cognito idToken 拿到真實 email。
- `showTerms` 攔截目前依賴 tracker 自帶 modal；如果生產發現有用戶被 modal 卡住的反饋，可考慮把 modal 樣式與站點主題整合。
