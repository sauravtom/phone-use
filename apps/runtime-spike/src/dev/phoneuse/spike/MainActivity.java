package dev.phoneuse.spike;

import android.app.Activity;
import android.os.Build;
import android.os.Bundle;
import android.content.Intent;
import android.system.Os;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/** Research APK: app-UID execution only. No model keys, broad storage, or external IPC. */
public class MainActivity extends Activity {
    private TextView output;
    private volatile boolean cancelled;
    private volatile Process process;
    private volatile Thread worker;
    private JSONObject report;
    private File root;
    private String runner;
    private String loader;
    private String libs;
    private final Object reportLock = new Object();

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        Button run = new Button(this); run.setText("Run diagnostics");
        Button cancel = new Button(this); cancel.setText("Cancel");
        Button export = new Button(this); export.setText("Export report");
        output = new TextView(this); output.setTextIsSelectable(true);
        ScrollView scroll = new ScrollView(this); scroll.addView(output);
        layout.addView(run); layout.addView(cancel); layout.addView(export); layout.addView(scroll);
        setContentView(layout);
        getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        try {
            File saved = new File(getFilesDir(), "report.json");
            if (saved.exists()) {
                report = new JSONObject(read(new FileInputStream(saved), 2_000_000));
                if ("running".equals(report.optString("state"))) {
                    report.put("state", "interrupted"); persist();
                }
                output.setText(report.toString(2));
            }
        } catch (Exception e) { output.setText(e.toString()); }
        run.setOnClickListener(v -> start());
        cancel.setOnClickListener(v -> { cancelled = true; Process p = process; if (p != null) p.destroy(); });
        export.setOnClickListener(v -> {
            Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
            intent.setType("application/json"); intent.putExtra(Intent.EXTRA_TITLE, "runtime-spike.json");
            intent.addCategory(Intent.CATEGORY_OPENABLE); startActivityForResult(intent, 10);
        });
        if (getIntent().getBooleanExtra("runDiagnostics", false)) start();
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == 10 && result == RESULT_OK && data != null && data.getData() != null) {
            synchronized (reportLock) {
                try (OutputStream out = getContentResolver().openOutputStream(data.getData())) {
                    if (report != null) out.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
                } catch (Exception e) { output.setText(e.toString()); }
            }
        }
    }
    @Override protected void onDestroy() {
        cancelled = true; Process p = process; if (p != null) p.destroy();
        super.onDestroy();
    }
    private void start() {
        if (worker != null && worker.isAlive()) return;
        cancelled = false;
        worker = new Thread(() -> {
            try { diagnostics(); }
            catch (Exception e) { add("harness", "failed", e.toString(), 0, -1); }
            finally {
                synchronized (reportLock) {
                    try { report.put("state", cancelled ? "cancelled" : "finished"); persist(); }
                    catch (Exception ignored) { }
                }
                show();
            }
        }, "runtime-diagnostics"); worker.start();
    }
    private void diagnostics() throws Exception {
        root = new File(getFilesDir(), "rootfs");
        runner = getApplicationInfo().nativeLibraryDir + "/libspike_runner.so";
        File compatibility = new File(getFilesDir(), "native-links"); compatibility.mkdirs();
        File talloc = new File(compatibility, "libtalloc.so.2");
        if (!talloc.exists() && new File(getApplicationInfo().nativeLibraryDir + "/libtalloc.so").exists())
            Os.symlink(getApplicationInfo().nativeLibraryDir + "/libtalloc.so", talloc.toString());
        boolean arm = Build.SUPPORTED_ABIS[0].startsWith("arm64");
        String arch = arm ? "aarch64-linux-gnu" : "x86_64-linux-gnu";
        loader = root + "/usr/lib/" + arch + "/" + (arm ? "ld-linux-aarch64.so.1" : "ld-linux-x86-64.so.2");
        libs = root + "/usr/lib/" + arch + ":" + root + "/lib/" + arch;
        synchronized (reportLock) {
            report = new JSONObject();
            report.put("schema", 1).put("state", "running").put("startedAt", System.currentTimeMillis())
                .put("package", getPackageName()).put("uid", android.os.Process.myUid())
                .put("androidApi", Build.VERSION.SDK_INT).put("androidRelease", Build.VERSION.RELEASE)
                .put("device", Build.MANUFACTURER + " " + Build.MODEL).put("fingerprint", Build.FINGERPRINT)
                .put("abis", new JSONArray(Arrays.asList(Build.SUPPORTED_ABIS)))
                .put("targetSdk", getApplicationInfo().targetSdkVersion)
                .put("build", new JSONObject(read(getAssets().open("build.json"), 100_000)))
                .put("checks", new JSONArray()); persist();
        }
        check("apk_native_exec", 5, null, runner, "--probe");
        check("android_shell_child", 5, null, "/system/bin/sh", "-c", "id; cat /proc/self/attr/current; echo CHILD_OK");
        File copy = new File(getFilesDir(), "copied-runner");
        try (InputStream in = new FileInputStream(runner); OutputStream out = new FileOutputStream(copy)) {
            transfer(in, out, 10_000_000);
        }
        copy.setExecutable(true, true);
        check("writable_native_exec", 5, null, copy.toString(), "--probe");
        check("timeout_owned_group", 1, null, "/system/bin/sh", "-c", "sleep 30 & wait");
        long began = System.currentTimeMillis();
        try { install(); add("runtime_install", "passed", "Verified every file before activation", System.currentTimeMillis()-began, 0); }
        catch (Exception e) { add("runtime_install", "failed", e.toString(), System.currentTimeMillis()-began, -1); return; }
        String bash = file("usr/bin/bash");
        check("ubuntu_loader", 10, null, loader, "--version");
        check("ubuntu_bash", 10, null, loader, "--library-path", libs, bash, "--noprofile", "--norc", "-c", "printf 'BASH_OK %s\\n' \"$BASH_VERSION\"");
        check("ubuntu_python", 20, null, loader, "--library-path", libs, file("usr/bin/python3"), "-c",
              "import sys,json,os; p=os.path.join(os.environ['HOME'],'fixture with spaces.json'); open(p,'w').write(json.dumps({'ok':True})); assert json.load(open(p))['ok']; print(sys.version); print('PYTHON_OK')");
        check("direct_absolute_child", 10, null, loader, "--library-path", libs, bash, "-c", "/usr/bin/python3 -c 'print(123)' ");
        check("direct_explicit_loader_child", 20, null, loader, "--library-path", libs, bash, "-c",
              "\"$SPIKE_LOADER\" --library-path \"$SPIKE_LIBS\" \"$SPIKE_ROOT/usr/bin/python3\" -c 'print(456)'");
        check("ubuntu_git_version", 10, null, loader, "--library-path", libs, file("usr/bin/git"), "--version");
        check("ubuntu_https", 40, null, loader, "--library-path", libs, file("usr/bin/curl"), "--fail", "--max-time", "25", "--head", "https://example.com");
        File repo = new File(getFilesDir(), "fixture-repo"); repo.mkdirs();
        check("git_init", 10, null, loader, "--library-path", libs, file("usr/bin/git"), "init", repo.toString());
        try (FileWriter w = new FileWriter(new File(repo, "hello.txt"))) { w.write("synthetic fixture\n"); }
        check("git_add", 10, null, loader, "--library-path", libs, file("usr/bin/git"), "-C", repo.toString(), "add", "hello.txt");
        check("git_commit", 10, null, loader, "--library-path", libs, file("usr/bin/git"), "-C", repo.toString(), "-c", "user.name=Runtime Spike", "-c", "user.email=spike@example.invalid", "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "fixture");
        String proot = getApplicationInfo().nativeLibraryDir + "/libproot.so";
        if (new File(proot).exists()) {
            check("proot_version", 10, null, proot, "--version");
            check("proot_child_chain", 40, null, proot, "-r", root.toString(), "-b", "/dev", "-b", "/proc", "-b", "/system", "-w", "/tmp", "/usr/bin/bash", "-c", "/usr/bin/python3 -c 'print(789)'; /usr/bin/git --version");
        } else add("proot_child_chain", "not_run", "PRoot binary not included in this build", 0, -1);
        String codex = file("opt/codex");
        String packagedCodex = getApplicationInfo().nativeLibraryDir + "/libcodex.so";
        if (new File(packagedCodex).exists()) check("packaged_codex_version", 30, null, packagedCodex, "--version");
        if (new File(codex).exists()) {
            check("codex_version", 30, null, codex, "--version");
            check("codex_protocol", 30,
                  "{\"id\":1,\"method\":\"initialize\",\"params\":{\"clientInfo\":{\"name\":\"runtime-spike\",\"title\":\"Runtime Spike\",\"version\":\"0.1\"}}}\n{\"method\":\"initialized\"}\n",
                  codex, "app-server", "--listen", "stdio://");
        } else add("codex_protocol", "not_run", "Codex binary not included in this build", 0, -1);
        add("authenticated_agent_task", "not_run", "No provider credentials requested or copied", 0, -1);
        add("claude_runtime", "not_run", "Claude runtime not included in this first probe", 0, -1);
        add("lifecycle_storage_privacy_matrix", "not_run", "Requires separate fault-injection and lifecycle validation", 0, -1);
    }
    private String file(String name) { return new File(root, name).toString(); }
    private void check(String name, int timeout, String input, String... command) {
        if (cancelled) { add(name, "not_run", "Cancelled", 0, -1); return; }
        long start = System.currentTimeMillis();
        try {
            ArrayList<String> args = new ArrayList<>();
            args.add(runner); args.add(Integer.toString(timeout)); Collections.addAll(args, command);
            ProcessBuilder builder = new ProcessBuilder(args).redirectErrorStream(true);
            builder.directory(getFilesDir());
            Map<String,String> env = builder.environment(); env.clear();
            env.put("PATH", "/system/bin"); env.put("HOME", getFilesDir().toString());
            env.put("TMPDIR", getCacheDir().toString()); env.put("LANG", "C.UTF-8");
            env.put("PYTHONHOME", file("usr")); env.put("GIT_EXEC_PATH", file("usr/lib/git-core"));
            env.put("GIT_TEMPLATE_DIR", file("usr/share/git-core/templates"));
            env.put("SSL_CERT_FILE", file("etc/ssl/certs/ca-certificates.crt"));
            env.put("CURL_CA_BUNDLE", file("etc/ssl/certs/ca-certificates.crt"));
            env.put("SPIKE_ROOT", root.toString()); env.put("SPIKE_LOADER", loader); env.put("SPIKE_LIBS", libs);
            env.put("LD_LIBRARY_PATH", new File(getFilesDir(), "native-links") + ":" + getApplicationInfo().nativeLibraryDir);
            env.put("PROOT_TMP_DIR", getCacheDir().toString());
            env.put("PROOT_LOADER", getApplicationInfo().nativeLibraryDir + "/libproot_loader.so");
            env.put("PROOT_NO_SECCOMP", "1");
            process = builder.start();
            try (OutputStream stdin = process.getOutputStream()) {
                if (input != null) stdin.write(input.getBytes(StandardCharsets.UTF_8));
            }
            String text = read(process.getInputStream(), 32_000);
            int exit = process.waitFor(); process = null;
            boolean ok = name.equals("timeout_owned_group") ? exit == 124 : exit == 0;
            if (name.equals("codex_protocol")) ok = ok && text.contains("\"result\"") && text.contains("\"id\":1");
            add(name, cancelled ? "cancelled" : ok ? "passed" : "failed", text, System.currentTimeMillis()-start, exit);
        } catch (Exception e) { add(name, cancelled ? "cancelled" : "failed", e.toString(), System.currentTimeMillis()-start, -1); }
        finally { Process p = process; if (p != null) p.destroy(); process = null; }
    }
    private void install() throws Exception {
        byte[] manifestBytes;
        try (InputStream in = getAssets().open("runtime-manifest.json")) {
            manifestBytes = read(in, 10_000_000).getBytes(StandardCharsets.UTF_8);
        }
        String manifestHash = hex(MessageDigest.getInstance("SHA-256").digest(manifestBytes));
        synchronized (reportLock) { report.put("runtimeManifestSha256", manifestHash); }
        File marker = new File(getFilesDir(), "runtime-installed");
        if (marker.exists() && manifestHash.equals(read(new FileInputStream(marker), 1000)) && root.isDirectory()) return;
        JSONObject manifest = new JSONObject(new String(manifestBytes, StandardCharsets.UTF_8));
        long expected = manifest.getLong("uncompressedBytes");
        if (expected > 800_000_000 || getFilesDir().getUsableSpace() < expected + 100_000_000)
            throw new IOException("Insufficient storage or oversized pack");
        File staging = new File(getFilesDir(), "rootfs-staging"); remove(staging); staging.mkdirs();
        JSONArray files = manifest.getJSONArray("files");
        if (files.length() > 30000) throw new IOException("Too many files");
        HashMap<String,JSONObject> records = new HashMap<>();
        for (int i=0; i<files.length(); i++) {
            JSONObject item = files.getJSONObject(i); String path = item.getString("path");
            safe(staging, path);
            if (records.put(path, item) != null) throw new IOException("Duplicate path");
        }
        long total = 0;
        Set<String> seen = new HashSet<>();
        try (ZipInputStream zip = new ZipInputStream(getAssets().open("runtime.zip"))) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                if (cancelled) throw new IOException("Cancelled installation");
                JSONObject item = records.get(entry.getName());
                if (item == null || item.has("link") || !seen.add(entry.getName())) throw new IOException("Unexpected entry");
                File dest = safe(staging, entry.getName()); dest.getParentFile().mkdirs();
                MessageDigest hash = MessageDigest.getInstance("SHA-256");
                long size = 0; byte[] bytes = new byte[32768]; int n;
                try (OutputStream out = new FileOutputStream(dest)) {
                    while ((n = zip.read(bytes)) != -1) {
                        size += n; total += n;
                        if (size > item.getLong("size") || total > expected) throw new IOException("Size mismatch");
                        hash.update(bytes, 0, n); out.write(bytes, 0, n);
                    }
                }
                if (size != item.getLong("size") || !hex(hash.digest()).equals(item.getString("sha256")))
                    throw new IOException("Hash mismatch: " + entry.getName());
                dest.setExecutable(item.getBoolean("executable"), true);
            }
        }
        for (int i=0; i<files.length(); i++) {
            JSONObject item = files.getJSONObject(i);
            if (!item.has("link") && !seen.contains(item.getString("path"))) throw new IOException("Missing file");
        }
        // Links are created after file extraction, so no ZIP entry traverses a link.
        for (int i=0; i<files.length(); i++) {
            JSONObject item = files.getJSONObject(i);
            if (item.has("link")) {
                File dest = safe(staging, item.getString("path"));
                String target = item.getString("link");
                if (target.startsWith("/")) throw new IOException("Absolute link");
                File resolved = new File(dest.getParentFile(), target);
                if (!resolved.getCanonicalPath().startsWith(staging.getCanonicalPath() + "/"))
                    throw new IOException("Escaping link");
                dest.getParentFile().mkdirs(); Os.symlink(target, dest.toString());
            }
        }
        remove(root);
        if (!staging.renameTo(root)) throw new IOException("Activation failed");
        new File(root, "tmp").mkdirs();
        new File(root, "dev").mkdirs();
        new File(root, "proc").mkdirs();
        try (FileWriter out = new FileWriter(marker)) { out.write(manifestHash); }
    }
    private static File safe(File base, String path) throws IOException {
        if (path.startsWith("/") || Arrays.asList(path.split("/")).contains("..")) throw new IOException("Invalid path");
        File dest = new File(base, path);
        if (!dest.getCanonicalPath().startsWith(base.getCanonicalPath() + "/")) throw new IOException("Escaping path");
        return dest;
    }
    private static void remove(File f) throws IOException {
        // Never follow symlinks while clearing task-owned staging or the old fixture.
        if (java.nio.file.Files.isSymbolicLink(f.toPath())) { if (!f.delete()) throw new IOException("unlink failed"); return; }
        File[] children = f.listFiles(); if (children != null) for (File child : children) remove(child);
        if (f.exists() && !f.delete()) throw new IOException("delete failed: " + f);
    }
    private void add(String name, String status, String text, long duration, int exit) {
        synchronized (reportLock) {
            try {
                report.getJSONArray("checks").put(new JSONObject().put("name", name).put("status", status)
                    .put("output", text).put("durationMs", duration).put("exitCode", exit)); persist();
            } catch (Exception e) { android.util.Log.e("RuntimeSpike", "Report write failed", e); }
        } show();
    }
    private void persist() throws Exception {
        File next = new File(getFilesDir(), "report.next");
        try (FileOutputStream out = new FileOutputStream(next)) {
            out.write(report.toString(2).getBytes(StandardCharsets.UTF_8)); out.getFD().sync();
        }
        if (!next.renameTo(new File(getFilesDir(), "report.json"))) throw new IOException("Report rename failed");
    }
    private void show() {
        runOnUiThread(() -> { synchronized (reportLock) { try { output.setText(report.toString(2)); } catch (Exception ignored) {} } });
    }
    private static String hex(byte[] bytes) {
        StringBuilder s = new StringBuilder(); for (byte b : bytes) s.append(String.format(Locale.ROOT, "%02x", b & 255)); return s.toString();
    }
    private static String read(InputStream in, int limit) throws IOException {
        // Drain beyond the display limit to avoid deadlocking a noisy subprocess.
        try (InputStream source = in; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] b = new byte[8192]; int n; boolean truncated = false;
            while ((n = source.read(b)) != -1) {
                int keep = Math.min(n, Math.max(0, limit - out.size()));
                out.write(b, 0, keep); if (keep < n) truncated = true;
            }
            return out.toString("UTF-8") + (truncated ? "\n[output truncated]" : "");
        }
    }
    private static void transfer(InputStream in, OutputStream out, long limit) throws IOException {
        byte[] b = new byte[8192]; long count = 0; int n;
        while ((n = in.read(b)) != -1) { count += n; if (count > limit) throw new IOException("Copy limit"); out.write(b, 0, n); }
    }
}
