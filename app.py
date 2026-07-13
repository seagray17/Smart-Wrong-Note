import streamlit as st
import json
import hashlib
from urllib.request import Request, urlopen
from supabase import create_client, Client

# 🤖 구글 Gemini 라이브러리 로드
try:
    from google import genai
except ImportError:
    st.error("⚠️ 라이브러리 누락! requirements.txt 파일에 'google-genai'를 추가한 후 GitHub에 올려주세요.")

# 내장 연동 정보
SUPABASE_URL = "https://kktrkhfpxeavhaugzohd.supabase.co"
SUPABASE_KEY = "sb_publishable_c0dtskcvaF1CjK9fZwBm-g_XgRg6hXH"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1526179676924674131/BiC8_dzOucdmx6-8j--22MNpbeGdIwCdQr8x_9B0goOYb68m0Q0cKCy8vFz8sLElX0wo"

# 🔒 Secrets 로드
ADMIN_MASTER_PASSWORD = st.secrets.get("ADMIN_MASTER_PASSWORD", "admin1234")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()
st.set_page_config(page_title="스마트 오답노트 마스터", layout="wide")

# 🔒 비밀번호 암호화 함수 (SHA-256)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# 디스코드 알림 함수
def send_discord_notification(name, text):
    if not DISCORD_WEBHOOK_URL or "YOUR_WEBHOOK" in DISCORD_WEBHOOK_URL: return
    payload = {"embeds": [{"title": "✉️ 새로운 개발자 피드백!", "color": 5814783, "fields": [{"name": "👤 작성자", "value": name, "inline": True}, {"name": "✍️ 내용", "value": text, "inline": False}]}]}
    try:
        req = Request(DISCORD_WEBHOOK_URL, data=json.dumps(payload).encode('utf-8'))
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urlopen(req) as response: pass
    except: pass

# Session State 초기화 (로그인 상태 기억)
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# 사이드바 레이아웃
with st.sidebar:
    st.header("👤 회원 시스템")
    
    if not st.session_state["logged_in"]:
        auth_mode = st.radio("모드를 선택하세요", ["로그인", "회원가입"])
        input_name = st.text_input("이름(닉네임)", value="").strip()
        input_password = st.text_input("비밀번호", value="", type="password").strip()
        
        if auth_mode == "회원가입":
            if st.button("📝 회원가입 하기", use_container_width=True):
                if not input_name or not input_password:
                    st.error("이름과 비밀번호를 모두 입력해주세요.")
                else:
                    try:
                        # 중복 유저 체크
                        user_check = supabase.table("users").select("*").eq("user_name", input_name).execute()
                        if user_check.data:
                            st.error("이미 존재하는 이름입니다. 다른 이름을 사용해주세요.")
                        else:
                            # 비밀번호 암호화 후 저장
                            supabase.table("users").insert({
                                "user_name": input_name,
                                "password_hash": hash_password(input_password)
                            }).execute()
                            st.success("🎉 회원가입 성공! 로그인 모드로 변경해 접속하세요.")
                    except Exception as e:
                        st.error(f"회원가입 실패: {e}")
                        
        elif auth_mode == "로그인":
            if st.button("🔒 로그인 하기", use_container_width=True):
                if not input_name or not input_password:
                    st.error("이름과 비밀번호를 입력해주세요.")
                else:
                    try:
                        # 유저 정보 가져오기
                        user_res = supabase.table("users").select("*").eq("user_name", input_name).execute()
                        if user_res.data and user_res.data[0]["password_hash"] == hash_password(input_password):
                            st.session_state["logged_in"] = True
                            st.session_state["username"] = input_name
                            st.success(f"👋 {input_name}님 환영합니다!")
                            st.rerun()
                        else:
                            st.error("이름 또는 비밀번호가 올바르지 않습니다.")
                    except Exception as e:
                        st.error(f"로그인 오류: {e}")
    else:
        st.success(f"🟢 로그인 됨: {st.session_state['username']} 님")
        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["show_wrong_notes"] = False
            st.rerun()

    st.divider()
    st.header("⚙️ 시험지 선택")
    exam_id = st.text_input("시험 이름 입력", value="2026년 3월 고3 수학", key="search_exam_id")
    st.divider()
    st.header("🔒 관리자 전용 인증")
    admin_password_input = st.text_input("관리자 암호", value="", type="password").strip()
    st.divider()
    st.header("✉️ 개발자에게 한마디")
    with st.form(key="feedback_form", clear_on_submit=True):
        feedback_text = st.text_area("피드백 내용", max_chars=500)
        if st.form_submit_button("🚀 피드백 전송", use_container_width=True):
            if feedback_text.strip():
                sender = st.session_state["username"] if st.session_state["logged_in"] else "익명"
                try:
                    supabase.table("feedbacks").insert({"user_name": sender, "content": feedback_text.strip()}).execute()
                    send_discord_notification(sender, feedback_text.strip())
                    st.success("💖 피드백 전달 완료!")
                except Exception as e: st.error(f"실패: {e}")

# 로그인 안 되어 있으면 메인 화면 차단
if not st.session_state["logged_in"]:
    st.title("📊 스마트 오답노트 마스터")
    st.info("💡 서비스를 이용하시려면 왼쪽 사이드바에서 **로그인**을 진행해 주세요. 계정이 없다면 회원가입 후 이용 가능합니다.")
    st.stop()

# 여기서부터는 로그인 성공한 유저만 볼 수 있음
user_name = st.session_state["username"]

tab1, tab2, tab3 = st.tabs(["📝 모의고사 채점하기", "⚙️ 새 시험지 정답 등록하기", "🔍 내가 쓴 오답노트 모아보기"])

# ==========================================
# 탭 1: 채점 및 오답노트
# ==========================================
with tab1:
    st.title("📊 스마트 오답노트 채점기")
    
    questions_db = []
    try: res = supabase.table("questions").select("*").eq("exam_id", exam_id.strip()).execute(); questions_db = res.data
    except Exception as e: st.error(f"DB 오류: {e}")

    if questions_db: st.success(f"📅 **{exam_id}** 시험지 로드 완료 (총 {len(questions_db)}문항)")
    else: st.warning(f"⚠️ '{exam_id}'은(는) 아직 등록되지 않은 시험지입니다.")

    with st.form(key="marking_form"):
        st.subheader("✍️ 내 답안 마킹")
        user_answers = {}
        total_q = len(questions_db) if questions_db else 20
        num_rows = (total_q + 3) // 4
        for row in range(num_rows):
            cols = st.columns(4)
            for col_idx in range(4):
                q_num = row * 4 + col_idx + 1
                if q_num <= total_q:
                    with cols[col_idx]: user_answers[str(q_num)] = st.text_input(f"{q_num}번 답", key=f"q_{q_num}")
        submit_marking = st.form_submit_button("🚀 전 문항 일괄 채점하기", type="primary")

    if submit_marking or st.session_state.get("show_wrong_notes", False):
        st.session_state["show_wrong_notes"] = True
        if not questions_db: st.error("등록되지 않은 시험지입니다.")
        else:
            wrong_questions = []
            correct_count = 0
            # 이제 password 조건 없이 user_name만으로 조회 (이미 안전하게 로그인 검증됨)
            notes_res = supabase.table("wrong_notes").select("*").eq("exam_id", exam_id.strip()).eq("user_name", user_name).execute()
            saved_memos = {str(n["question_number"]): n["user_memo"] for n in notes_res.data}
            questions_db.sort(key=lambda x: x["question_number"])
            
            for q in questions_db:
                q_num_str = str(q["question_number"])
                user_ans = user_answers.get(q_num_str, "").strip()
                correct_ans = str(q["answer"]).strip()
                if user_ans == correct_ans: correct_count += 1
                else: wrong_questions.append({"question_number": q["question_number"], "correct_answer": correct_ans, "user_answer": user_ans if user_ans else "(미제출)", "saved_memo": saved_memos.get(q_num_str, "")})
            
            st.success(f"💯 내 성적: {correct_count}/{len(questions_db)}")
            if len(wrong_questions) == 0: st.balloons()
            else:
                for item in wrong_questions:
                    with st.form(key=f"wrong_note_form_{item['question_number']}"):
                        st.markdown(f"### ❓ {item['question_number']}번 문제 (정답: {item['correct_answer']})")
                        user_memo = st.text_area("오답 메모", value=item['saved_memo'], key=f"memo_{item['question_number']}")
                        if st.form_submit_button("💾 오답 저장"):
                            try:
                                check_res = supabase.table("wrong_notes").select("*").eq("exam_id", exam_id.strip()).eq("question_number", str(item['question_number'])).eq("user_name", user_name).execute()
                                if check_res.data: 
                                    supabase.table("wrong_notes").update({"user_memo": user_memo}).eq("exam_id", exam_id.strip()).eq("question_number", str(item['question_number'])).eq("user_name", user_name).execute()
                                else: 
                                    # password 필드는 DB 구조 호환성을 위해 빈 문자열 혹은 생략 처리 (여기선 빈 값 처리)
                                    supabase.table("wrong_notes").insert({"exam_id": exam_id.strip(), "question_number": str(item['question_number']), "user_name": user_name, "password": "", "user_memo": user_memo}).execute()
                                st.toast("저장 완료!")
                            except Exception as e: st.error(f"실패: {e}")

# ==========================================
# 탭 2: 🤖 AI 초고속 자동 정답 등록기
# ==========================================
with tab2:
    st.title("⚙️ AI 모의고사 정답 초고속 등록기")
    st.info("💡 인터넷(EBSi 등)에서 정답표 텍스트를 대충 긁어서 넣으면 AI가 알아서 정답만 뽑아 등록합니다!")
    
    with st.form(key="register_form"):
        c1, c2, c3, c4 = st.columns(4)
        with c1: reg_year = st.number_input("년도", value=2026, step=1)
        with c2: reg_month = st.number_input("월", value=3, step=1)
        with c3: reg_grade = st.selectbox("학년", ["고1", "고2", "고3"], index=2)
        with c4: reg_subject = st.text_input("과목", value="수학")
        
        st.subheader("🤖 AI 자동 가공창")
        raw_text_input = st.text_area("정답표 텍스트 붙여넣기", placeholder="예시: [1] ③  [2] ① ...")
        submit_registration = st.form_submit_button("🔥 AI를 통해 정답지 자동 등록하기", type="primary")

    if submit_registration:
        if admin_password_input != ADMIN_MASTER_PASSWORD:
            st.error("❌ 관리자 비밀번호가 올바르지 않습니다.")
        elif not raw_text_input.strip():
            st.error("❌ 정답표 텍스트를 입력해 주세요.")
        elif not GEMINI_API_KEY:
            st.error("❌ Secrets에 GEMINI_API_KEY가 없습니다.")
        else:
            reg_exam_id = f"{reg_year}년 {reg_month}월 {reg_grade} {reg_subject}"
            with st.spinner("🤖 Gemini AI가 지저분한 텍스트에서 정답을 분석하는 중..."):
                try:
                    client = genai.Client(api_key=GEMINI_API_KEY)
                    prompt = f"다음 텍스트는 모의고사 정답표입니다. 문항 정답 숫자만 순서대로 공백으로 구분해서 출력해줘. 예시 결과: '3 1 5 4'\n\n{raw_text_input}"
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    ans_list = response.text.strip().split()
                    
                    if not ans_list: st.error("AI가 정답을 추출하는 데 실패했습니다.")
                    else:
                        st.write("🤖 **AI 추출 결과 파싱 성공!** 문항 수:", len(ans_list))
                        supabase.table("questions").delete().eq("exam_id", reg_exam_id).execute()
                        bulk_data = [{"year": reg_year, "month": reg_month, "grade": reg_grade, "subject": reg_subject, "exam_id": reg_exam_id, "question_number": i + 1, "answer": ans, "concept_tags": []} for i, ans in enumerate(ans_list)]
                        supabase.table("questions").insert(bulk_data).execute()
                        st.balloons(); st.success(f"🎉 '{reg_exam_id}' {len(ans_list)}문항 자동 등록 완료!")
                except Exception as e: st.error(f"AI 자동 등록 실패: {e}")

# ==========================================
# 탭 3: 오답노트 보관함
# ==========================================
with tab3:
    st.title("🔍 내 손안의 오답노트 보관함")
    try:
        exam_res = supabase.table("wrong_notes").select("exam_id").eq("user_name", user_name).execute()
        exam_list = list(set([n["exam_id"].strip() for n in exam_res.data])) if exam_res.data else []
    except: exam_list = []

    if not exam_list: st.info("일치하는 오답 메모가 없습니다.")
    else:
        selected_exam = st.selectbox("복습할 시험지 선택", exam_list)
        if selected_exam:
            notes_res = supabase.table("wrong_notes").select("*").eq("exam_id", selected_exam.strip()).eq("user_name", user_name).execute()
            q_res = supabase.table("questions").select("*").eq("exam_id", selected_exam.strip()).execute()
            questions_dict = {str(q["question_number"]).strip(): q for q in q_res.data} if q_res.data else {}

            for note in notes_res.data:
                q_num_str = str(note["question_number"]).strip()
                correct_ans = questions_dict.get(q_num_str, {}).get("answer", "알 수 없음")
                with st.form(key=f"review_{q_num_str}"):
                    st.markdown(f"### ❓ {q_num_str}번 문제 (정답: `{correct_ans}`)")
                    new_memo = st.text_area("오답 기록 수정", value=note["user_memo"])
                    c1, c2, _ = st.columns([1, 1, 8])
                    with c1:
                        if st.form_submit_button("📝 수정"):
                            supabase.table("wrong_notes").update({"user_memo": new_memo}).eq("exam_id", selected_exam.strip()).eq("question_number", q_num_str).eq("user_name", user_name).execute()
                            st.rerun()
                    with c2:
                        if st.form_submit_button("🗑️ 삭제"):
                            supabase.table("wrong_notes").delete().eq("exam_id", selected_exam.strip()).eq("question_number", q_num_str).eq("user_name", user_name).execute()
                            st.rerun()