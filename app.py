import streamlit as st
import json
from urllib.request import Request, urlopen
from supabase import create_client, Client

# [내장 완료] 제공해주신 Supabase 연동 정보
SUPABASE_URL = "https://kktrkhfpxeavhaugzohd.supabase.co"
SUPABASE_KEY = "sb_publishable_c0dtskcvaF1CjK9fZwBm-g_XgRg6hXH"

# 디스코드 웹훅 주소
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1526179676924674131/BiC8_dzOucdmx6-8j--22MNpbeGdIwCdQr8x_9B0goOYb68m0Q0cKCy8vFz8sLElX0wo"

# 🔒 [보안 강화] 스트림릿 Secrets 환경변수에서 비밀번호를 안전하게 로드합니다.
# 만약 세팅 전이거나 에러가 날 경우를 대비해 디폴트 값('admin1234')을 지정해둡니다.
if "ADMIN_MASTER_PASSWORD" in st.secrets:
    ADMIN_MASTER_PASSWORD = st.secrets["ADMIN_MASTER_PASSWORD"]
else:
    ADMIN_MASTER_PASSWORD = "admin1234"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

st.set_page_config(page_title="스마트 오답노트 마스터", layout="wide")

# 디스코드 알림 전송 함수
def send_discord_notification(name, text):
    if not DISCORD_WEBHOOK_URL or "YOUR_WEBHOOK" in DISCORD_WEBHOOK_URL:
        return

    payload = {
        "embeds": [
            {
                "title": "✉️ 새로운 개발자 피드백이 도착했습니다!",
                "color": 5814783,
                "fields": [
                    {"name": "👤 작성자", "value": name, "inline": True},
                    {"name": "✍️ 내용", "value": text, "inline": False}
                ],
                "footer": {"text": "스마트 오답노트 마스터 앱 알림 시스템"}
            }
        ]
    }
    
    try:
        req = Request(DISCORD_WEBHOOK_URL, data=json.dumps(payload).encode('utf-8'))
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urlopen(req) as response:
            pass
    except Exception as e:
        print(f"디스코드 알림 실패: {e}")

# 사이드바 공통 레이아웃
with st.sidebar:
    st.header("👤 사용자 인증")
    user_name = st.text_input("내 이름(닉네임)을 입력하세요", value="홍길동").strip()
    user_password = st.text_input("비밀번호를 입력하세요", value="", type="password").strip()
    
    st.divider()
    st.header("⚙️ 시험지 선택")
    exam_id = st.text_input("시험 이름을 입력하세요", value="2026년 3월 고3 수학", key="search_exam_id")

    st.divider()
    # 🔒 악용 방지용 관리자 인증 구역
    st.header("🔒 관리자 전용 인증")
    st.caption("새 시험지 정답을 등록할 때만 마스터 비밀번호를 입력하세요.")
    admin_password_input = st.text_input("관리자 암호", value="", type="password").strip()

    st.divider()
    # 💬 개발자 피드백 수집 구역
    st.header("✉️ 개발자에게 한마디")
    st.caption("앱을 쓰면서 불편했던 점이나 바라는 점을 적어주시면 개발자에게 실시간 전송됩니다!")
    
    with st.form(key="feedback_form", clear_on_submit=True):
        feedback_text = st.text_area("피드백 내용", placeholder="여기에 의견을 입력하세요...", max_chars=500)
        submit_feedback = st.form_submit_button("🚀 피드백 전송하기", use_container_width=True)
        
        if submit_feedback:
            if not feedback_text.strip():
                st.error("내용을 입력한 뒤 전송해 주세요!")
            else:
                sender_name = user_name if user_name else "익명"
                try:
                    supabase.table("feedbacks").insert({
                        "user_name": sender_name,
                        "content": feedback_text.strip()
                    }).execute()
                    
                    send_discord_notification(sender_name, feedback_text.strip())
                    st.success("💖 피드백이 안전하게 전달되었습니다. 감사합니다!")
                except Exception as fb_err:
                    st.error(f"피드백 전송 실패: {fb_err}")

# 화면 상단 탭 구성
tab1, tab2, tab3 = st.tabs([
    "📝 모의고사 채점하기", 
    "⚙️ 새 시험지 정답 등록하기", 
    "🔍 내가 쓴 오답노트 모아보기"
])

# ==========================================
# 탭 1: 모의고사 채점 및 오답노트 (개인별 오답 저장)
# ==========================================
with tab1:
    st.title("📊 스마트 오답노트 채점기")
    st.caption(f"현재 **[{user_name}]** 님으로 접속 중입니다. 본인의 답안을 채점하세요.")

    if not user_name or not user_password:
        st.error("⚠️ 사이드바에 이름과 비밀번호를 모두 입력해 주셔야 오답노트 저장 및 조회가 가능합니다.")
        st.stop()

    questions_db = []
    try:
        res = supabase.table("questions").select("*").eq("exam_id", exam_id.strip()).execute()
        questions_db = res.data
    except Exception as e:
        st.error(f"DB 연결 오류: {e}")

    if questions_db:
        total_q = len(questions_db)
        st.success(f"📅 **{exam_id}** 시험지가 로드되었습니다. (총 {total_q}문항)")
    else:
        total_q = 20
        st.warning(f"⚠️ '{exam_id}'은(는) 아직 등록되지 않은 시험지입니다. [정답 등록하기] 탭에서 먼저 등록해 주세요.")

    with st.form(key="marking_form"):
        st.subheader(f"✍️ 내 답안 마킹 (1번 ~ {total_q}번)")
        user_answers = {}

        num_rows = (total_q + 3) // 4
        for row in range(num_rows):
            cols = st.columns(4)
            for col_idx in range(4):
                q_num = row * 4 + col_idx + 1
                if q_num <= total_q:
                    with cols[col_idx]:
                        user_answers[str(q_num)] = st.text_input(f"{q_num}번 답", key=f"q_{q_num}", value="")

        submit_marking = st.form_submit_button("🚀 전 문항 일괄 채점하기", type="primary")

    if submit_marking or st.session_state.get("show_wrong_notes", False):
        st.session_state["show_wrong_notes"] = True
        
        if not questions_db:
            st.error("등록되지 않은 시험지는 채점할 수 없습니다.")
        else:
            wrong_questions = []
            correct_count = 0
            
            notes_res = supabase.table("wrong_notes").select("*") \
                .eq("exam_id", exam_id.strip()) \
                .eq("user_name", user_name) \
                .eq("password", user_password) \
                .execute()
            saved_memos = {str(n["question_number"]): n["user_memo"] for n in notes_res.data}
            
            questions_db.sort(key=lambda x: x["question_number"])
            
            for q in questions_db:
                q_num_str = str(q["question_number"])
                user_ans = user_answers.get(q_num_str, "").strip() if user_answers else ""
                correct_ans = str(q["answer"]).strip()
                
                if user_ans == correct_ans:
                    correct_count += 1
                else:
                    wrong_questions.append({
                        "question_number": q["question_number"],
                        "correct_answer": correct_ans,
                        "user_answer": user_ans if user_ans else "(미제출)",
                        "saved_memo": saved_memos.get(q_num_str, "")
                    })
            
            score_str = f"{correct_count}/{total_q}"
            wrong_count = len(wrong_questions)
            
            st.success(f"💯 내 성적: {score_str}")
            
            if wrong_count == 0:
                st.balloons()
                st.info("와우! 만점입니다! 🎉")
            else:
                st.subheader(f"❌ 틀린 문제 오답 노트 ({wrong_count}문항)")
                st.caption("📝 메모를 적은 후 아래 [💾 이 문항 오답 저장] 버튼을 누르면 DB에 안전하게 저장됩니다.")
                
                for item in wrong_questions:
                    with st.form(key=f"wrong_note_form_{exam_id}_{item['question_number']}"):
                        st.markdown(f"### ❓ {item['question_number']}번 문제")
                        st.error(f"내가 제출한 답: {item['user_answer']}  |  **실제 정답: {item['correct_answer']}**")
                        
                        user_memo = st.text_area("오답 메모 입력", value=item['saved_memo'], key=f"input_{exam_id}_{item['question_number']}")
                        save_btn = st.form_submit_button("💾 이 문항 오답 저장")
                        
                        if save_btn:
                            save_data = {
                                "exam_id": exam_id.strip(), 
                                "question_number": str(item['question_number']).strip(),
                                "user_name": user_name, 
                                "password": user_password, 
                                "user_memo": user_memo
                            }
                            
                            try:
                                check_res = supabase.table("wrong_notes") \
                                    .select("*") \
                                    .eq("exam_id", exam_id.strip()) \
                                    .eq("question_number", str(item['question_number']).strip()) \
                                    .eq("user_name", user_name) \
                                    .eq("password", user_password) \
                                    .execute()
                                
                                if check_res.data:
                                    supabase.table("wrong_notes") \
                                        .update({"user_memo": user_memo}) \
                                        .eq("exam_id", exam_id.strip()) \
                                        .eq("question_number", str(item['question_number']).strip()) \
                                        .eq("user_name", user_name) \
                                        .eq("password", user_password) \
                                        .execute()
                                else:
                                    supabase.table("wrong_notes").insert(save_data).execute()
                                    
                                st.toast(f"🎉 {item['question_number']}번 오답노트 저장 완료!")
                            
                            except Exception as db_err:
                                st.error(f"❌ 데이터베이스 저장 실패: {db_err}")

# ==========================================
# 탭 2: 관리자용 [가변형 정답 등록기]
# ==========================================
with tab2:
    st.title("⚙️ 모의고사 정답 초고속 등록기")
    st.info("⚠️ 악용 방지를 위해 정답을 일괄 등록하려면 사이드바 하단의 **[🔒 관리자 전용 인증]** 암호가 정확해야 합니다.")
    
    with st.form(key="register_form"):
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1: reg_year = st.number_input("년도", value=2026, step=1)
        with col2: reg_month = st.number_input("월", value=3, step=1)
        with col3: reg_grade = st.selectbox("학년", ["고1", "고2", "고3"], index=2)
        with col4: reg_subject = st.text_input("과목", value="수학")
        with col5: reg_total_q = st.number_input("총 문항 수", value=20, min_value=1, max_value=100, step=1)

        st.subheader("📋 정답 일괄 입력")
        default_ans = " ".join(["1" if i%5==0 else "2" if i%5==1 else "3" if i%5==2 else "4" if i%5==3 else "5" for i in range(20)])
        raw_answers = st.text_input("정답 입력창", value=default_ans)

        submit_registration = st.form_submit_button("🔥 클릭 한 번으로 DB에 맞춤형 문항 일괄 등록", type="primary")

    if submit_registration:
        if admin_password_input != ADMIN_MASTER_PASSWORD:
            st.error("❌ 관리자 비밀번호가 올바르지 않습니다! 정답지 등록 권한이 없습니다.")
        else:
            reg_exam_id = f"{reg_year}년 {reg_month}월 {reg_grade} {reg_subject}"
            ans_list = raw_answers.strip().split()
            
            if len(ans_list) != reg_total_q:
                st.error(f"설정된 문항 수는 {reg_total_q}개인데, 입력된 정답은 {len(ans_list)}개입니다.")
            else:
                with st.spinner("Supabase DB에 정답지 생성 중..."):
                    try:
                        supabase.table("questions").delete().eq("exam_id", reg_exam_id).execute()
                        bulk_data = []
                        for i in range(reg_total_q):
                            row_data = {
                                "year": reg_year,
                                "month": reg_month,
                                "grade": reg_grade,
                                "subject": reg_subject,
                                "exam_id": reg_exam_id,
                                "question_number": i + 1,
                                "answer": ans_list[i],
                                "concept_tags": [] 
                            }
                            bulk_data.append(row_data)
                        
                        supabase.table("questions").insert(bulk_data).execute()
                        st.balloons()
                        st.success(f"🎉 '{reg_exam_id}' 등록 성공!")
                    except Exception as e:
                        st.error(f"등록 실패: {e}")

# ==========================================
# 탭 3: 내가 작성한 오답노트 보관함
# ==========================================
with tab3:
    st.title("🔍 내 손안의 오답노트 보관함")

    if not user_name or not user_password:
        st.warning("🔒 사이드바에 이름과 비밀번호를 입력하셔야 보관함을 열 수 있습니다.")
    else:
        try:
            exam_res = supabase.table("wrong_notes").select("exam_id") \
                .eq("user_name", user_name) \
                .eq("password", user_password) \
                .execute()
            exam_list = list(set([n["exam_id"].strip() for n in exam_res.data])) if exam_res.data else []
        except Exception as e:
            exam_list = []

        if not exam_list:
            st.info(f"💡 [{user_name}]님 정보 및 비밀번호와 정확히 일치하는 오답 메모가 없습니다. 다시 확인해 주세요.")
        else:
            selected_exam = st.selectbox("복습할 시험지를 선택하세요", exam_list, key="select_review_exam")

            if selected_exam:
                with st.spinner("오답 기록장 로드 중..."):
                    notes_res = supabase.table("wrong_notes").select("*") \
                        .eq("exam_id", selected_exam.strip()) \
                        .eq("user_name", user_name) \
                        .eq("password", user_password) \
                        .execute()
                    saved_notes = notes_res.data

                    q_res = supabase.table("questions").select("*").eq("exam_id", selected_exam.strip()).execute()
                    questions_dict = {str(q["question_number"]).strip(): q for q in q_res.data} if q_res.data else {}

                    if not saved_notes:
                        st.info("이 시험지에는 저장된 오답 메모가 없습니다.")
                    else:
                        st.subheader(f"📋 '{selected_exam}' 오답 복습 리스트 (총 {len(saved_notes)}문항)")
                        
                        saved_notes.sort(key=lambda x: int(str(x["question_number"]).strip()) if str(x["question_number"]).strip().isdigit() else 0)

                    for note in saved_notes:
                        q_num_str = str(note["question_number"]).strip()
                        q_info = questions_dict.get(q_num_str, {})
                        correct_ans = q_info.get("answer", "알 수 없음")

                        with st.form(key=f"review_form_{selected_exam}_{q_num_str}"):
                            st.markdown(f"### ❓ {q_num_str}번 문제")
                            st.markdown(f"**🎯 실제 정답:** `{correct_ans}`")
                            
                            new_memo = st.text_area("✍️ 오답 기록 수정", value=note["user_memo"], key=f"review_{selected_exam}_{q_num_str}")

                            col1, col2, col3 = st.columns([1, 1, 8])
                            
                            with col1:
                                edit_btn = st.form_submit_button("📝 수정")
                                if edit_btn:
                                    try:
                                        supabase.table("wrong_notes") \
                                            .update({"user_memo": new_memo}) \
                                            .eq("exam_id", selected_exam.strip()) \
                                            .eq("question_number", q_num_str) \
                                            .eq("user_name", user_name) \
                                            .eq("password", user_password) \
                                            .execute()
                                        st.toast("💡 오답 메모가 수정되었습니다!")
                                        st.rerun()
                                    except Exception as db_err:
                                        st.error(f"❌ 수정 실패: {db_err}")
                                        
                            with col2:
                                delete_btn = st.form_submit_button("🗑️ 삭제")
                                if delete_btn:
                                    try:
                                        supabase.table("wrong_notes").delete() \
                                            .eq("exam_id", selected_exam.strip()) \
                                            .eq("question_number", q_num_str) \
                                            .eq("user_name", user_name) \
                                            .eq("password", user_password) \
                                            .execute()
                                        st.toast(f"🗑️ {q_num_str}번 오답 기록이 영구 삭제되었습니다.")
                                        st.rerun()
                                    except Exception as db_err:
                                        st.error(f"❌ 삭제 실패: {db_err}")
                            with col3:
                                pass